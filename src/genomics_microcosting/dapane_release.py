# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify a pinned workforce quotation artifact without importing its runtime."""

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any, cast
from urllib.parse import urlsplit

MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
MAX_EXACT_DIGITS = 96
MAX_EXACT_SCALE = 36
DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _require(*, condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _object(value: object) -> dict[str, Any]:
    _require(condition=isinstance(value, dict), message="Expected a JSON object")
    return cast("dict[str, Any]", value)


def _records(value: object) -> list[dict[str, Any]]:
    _require(condition=isinstance(value, list), message="Expected a JSON record array")
    return [_object(item) for item in cast("list[object]", value)]


def _unique(value: object, key: str) -> dict[str, dict[str, Any]]:
    records = _records(value)
    _require(
        condition=all(isinstance(row.get(key), str) and row[key].strip() for row in records),
        message="Missing record identity",
    )
    keyed = {row[key]: row for row in records}
    _require(condition=len(keyed) == len(records), message="Duplicate record identity")
    return keyed


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False,
    ).encode()


def _no_float(value: str) -> None:
    message = f"Nonexact JSON numeric token: {value[:64]}"
    raise ValueError(message)


def _pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        _require(condition=key not in result, message="Duplicate JSON key")
        result[key] = value
    return result


def _date(value: object) -> date:
    _require(condition=isinstance(value, str), message="Date must be an ISO string")
    text = cast("str", value)
    parsed = date.fromisoformat(text)
    _require(condition=parsed.isoformat() == text, message="Date must use YYYY-MM-DD")
    return parsed


def load_workforce_artifact(raw: str | bytes, expected_digest: str) -> dict[str, Any]:
    """Validate exact JSON, canonical identity and the retained release snapshot.

    A caller-supplied digest identifies a selected artifact; it does not establish
    source authority or approve a new employer/classification mapping.
    """
    _require(condition=isinstance(raw, (str, bytes)), message="Artifact must be JSON text or bytes")
    payload = raw.encode() if isinstance(raw, str) else raw
    _require(condition=len(payload) <= MAX_ARTIFACT_BYTES, message="Artifact exceeds size bound")
    _require(
        condition=isinstance(expected_digest, str) and bool(DIGEST.fullmatch(expected_digest)),
        message="Expected artifact digest must be lowercase SHA-256",
    )
    try:
        envelope = _object(json.loads(
            payload, object_pairs_hook=_pairs,
            parse_float=_no_float, parse_constant=_no_float,
        ))
        unsigned = {k: v for k, v in envelope.items() if k != "artifact_sha256"}
        actual = sha256(_canonical(unsigned)).hexdigest()
        snapshot = _object(envelope.get("release_snapshot"))
        release_digest = sha256(_canonical(snapshot)).hexdigest()
    except (UnicodeError, RecursionError) as error:
        message = "Artifact is not bounded valid UTF-8 JSON"
        raise ValueError(message) from error
    _require(
        condition=envelope.get("artifact_sha256") == actual == expected_digest,
        message="Artifact digest does not match the pinned identity",
    )
    _require(condition=envelope.get("release_sha256") == release_digest, message="Release digest differs")
    _require(
        condition=set(envelope) == {
            "schema_version", "provider", "release_id", "as_known_on",
            "release_snapshot", "release_sha256", "bindings", "quotes",
            "artifact_sha256",
        },
        message="Unknown or missing artifact fields",
    )
    _require(
        condition=envelope.get("schema_version") == "workforce-dapane-quotes/1",
        message="Unsupported workforce artifact version",
    )
    provider = _object(envelope.get("provider"))
    _require(
        condition=provider.get("name") == "microcosting-healthworkforce"
        and provider.get("method_id") == "direct_unit_quote_v1"
        and isinstance(provider.get("version"), str)
        and bool(provider["version"].strip()),
        message="Unsupported provider identity or method",
    )
    _require(
        condition=snapshot.get("release_id") == envelope.get("release_id")
        and snapshot.get("as_known_on") == envelope.get("as_known_on")
        and snapshot.get("method_id") == "direct_unit_quote_v1",
        message="Release identity or knowledge date differs",
    )
    return envelope


def _string_array(value: object) -> list[str]:
    _require(
        condition=isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value),
        message="Source scope must be a nonempty array of nonblank strings",
    )
    return cast("list[str]", value)


def _decimal_projection(value: object) -> str:
    _require(condition=isinstance(value, str), message="Source amount must be an exact decimal string")
    try:
        number = Decimal(cast("str", value))
    except InvalidOperation as error:
        message = "Source amount must be a valid exact decimal string"
        raise ValueError(message) from error
    _require(
        condition=number.is_finite() and not number.is_signed(),
        message="Source amount must be finite and nonnegative",
    )
    parts = number.as_tuple()
    exponent = cast("int", parts.exponent)
    _require(
        condition=len(parts.digits) + max(exponent, 0) <= MAX_EXACT_DIGITS
        and -exponent <= MAX_EXACT_SCALE,
        message="Source amount exceeds the Dapane exact transport bounds",
    )
    return format(number, "f")


def _check_scope(
    snapshot: dict[str, Any], original: dict[str, Any], source: dict[str, Any],
) -> None:
    _require(condition=original.get("status") == "accepted", message="Quote must be accepted")
    employers = _string_array(source.get("employers"))
    classifications = _string_array(source.get("classifications"))
    _require(
        condition=source.get("kind") in {"synthetic", "published_wage_reference"}
        and source.get("holding") == "held"
        and source.get("authority") == "primary"
        and source.get("applicability") == "verified"
        and isinstance(source.get("sha256"), str)
        and bool(DIGEST.fullmatch(source["sha256"]))
        and source.get("sha256") == original.get("source_sha256"),
        message="Quote source evidence or hash differs",
    )
    _require(
        condition=source.get("jurisdiction") == snapshot.get("jurisdiction")
        and isinstance(snapshot.get("employer"), str)
        and snapshot.get("employer") in employers
        and isinstance(snapshot.get("classification"), str)
        and snapshot.get("classification") in classifications,
        message="Quote source employer or classification differs",
    )
    start, stop = _date(original.get("starts_on")), _date(original.get("ends_on"))
    source_start = _date(source.get("effective_from"))
    verified_stop = _date(source.get("verified_through"))
    _require(condition=source_start <= start < stop <= verified_stop, message="Quote source interval differs")
    if source.get("effective_to") is not None:
        _require(condition=stop <= _date(source["effective_to"]), message="Source effective interval differs")
    retrieved = datetime.fromisoformat(str(source.get("retrieved_at")))
    _require(
        condition=retrieved.utcoffset() is not None
        and retrieved.date() <= _date(snapshot.get("as_known_on"))
        and _date(original.get("known_from")) <= _date(snapshot.get("as_known_on")),
        message="Source is unavailable at the release knowledge date",
    )


def _check_projection(
    snapshot: dict[str, Any], binding: dict[str, Any],
    quote: dict[str, Any], original: dict[str, Any],
) -> None:
    _require(
        condition=binding.get("unit") == quote.get("unit") == "minute"
        and binding.get("per_quantity") == quote.get("per_quantity") == "60"
        and original.get("unit") == "hour",
        message="This recipe requires the explicit hour-to-minute binding",
    )
    components = quote.get("components")
    _require(
        condition=isinstance(components, list) and bool(components)
        and all(isinstance(c, str) and c.strip() for c in components)
        and len(set(components)) == len(components)
        and binding.get("components") == components
        and components == [original.get("component")]
        and isinstance(binding.get("component_basis"), str)
        and bool(binding["component_basis"].strip()),
        message="Component binding is missing, duplicated or inconsistent",
    )
    _require(
        condition=quote.get("target") == binding.get("target")
        and isinstance(quote.get("target"), str) and bool(quote["target"].strip())
        and type(quote.get("price_year")) is int
        and type(binding.get("price_year")) is int
        and quote.get("price_year") == binding.get("price_year")
        and quote.get("currency") == snapshot.get("currency")
        and quote.get("basis") == "financial_cost"
        and quote.get("kind") == "resource_use"
        and quote.get("amount") == _decimal_projection(original.get("amount"))
        and quote.get("valid_from") == original.get("starts_on")
        and quote.get("valid_to") == original.get("ends_on")
        and quote.get("known_from") == original.get("known_from"),
        message="Projected quote differs from its selected source binding",
    )


def selected_workforce_quote(
    raw: str | bytes, *, expected_digest: str, quote_id: str,
    service_date: str, knowledge_cutoff: str,
) -> dict[str, Any]:
    """Select one dated quote with intact source, component and binding lineage."""
    envelope = load_workforce_artifact(raw, expected_digest)
    snapshot = _object(envelope["release_snapshot"])
    quotes = _unique(envelope["quotes"], "id")
    bindings = _unique(envelope["bindings"], "quote_id")
    _require(condition=set(quotes) == set(bindings), message="Quote and binding coverage differs")
    _require(condition=quote_id in quotes, message="Unknown quote identity")
    quote, binding = quotes[quote_id], bindings[quote_id]
    originals = _unique(snapshot.get("quotes"), "quote_id")
    original = originals.get(binding.get("provider_quote_id"))
    _require(condition=original is not None, message="Unknown provider quote identity")
    original = cast("dict[str, Any]", original)
    registry = _object(snapshot.get("sources"))
    _require(
        condition=type(registry.get("schema_version")) is int
        and registry.get("schema_version") == 1,
        message="Unsupported source registry version",
    )
    sources = _unique(registry.get("records"), "source_id")
    source = sources.get(original.get("source_id"))
    _require(condition=source is not None, message="Unknown provider source identity")
    source = cast("dict[str, Any]", source)
    _check_scope(snapshot, original, source)
    _check_projection(snapshot, binding, quote, original)
    metadata = _object(quote.get("source"))
    synthetic = source.get("kind") == "synthetic"
    uri = str(source.get("uri"))
    parsed_uri = urlsplit(uri)
    _require(
        condition=parsed_uri.scheme in {"http", "https"} and bool(parsed_uri.hostname)
        and parsed_uri.username is None and parsed_uri.password is None,
        message="Source URI is not a public source locator",
    )
    _require(
        condition=metadata.get("id") == original.get("source_id")
        and metadata.get("version") == envelope.get("release_id")
        and metadata.get("content_digest") == "sha256:" + source["sha256"]
        and metadata.get("evidence") == ("synthetic" if synthetic else "observed")
        and metadata.get("validation") == ("unvalidated" if synthetic else "source_verified")
        and metadata.get("access") == "public"
        and metadata.get("locator") == uri,
        message="Projected quotation source metadata differs",
    )
    when, cutoff = _date(service_date), _date(knowledge_cutoff)
    _require(
        condition=_date(quote.get("valid_from")) <= when < _date(quote.get("valid_to")),
        message="Service date is outside the selected quotation interval",
    )
    _require(
        condition=_date(envelope.get("as_known_on")) <= cutoff
        and _date(quote.get("known_from")) <= cutoff,
        message="Quotation is unavailable at the requested knowledge cutoff",
    )
    return quote
