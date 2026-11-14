# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check that each compute sensitivity bound reaches the matching subtotal."""

import json
from pathlib import Path

from tests import checks


def test_genome_processing_bound_dependencies() -> None:
    """Each lower and upper subtotal must use its corresponding compute bound."""
    path = (
        Path(__file__).resolve().parent
        / "fixtures/t1_scenarios"
        / "t1-compute-bound-propagation-v2.json"
    )
    manifest = json.loads(path.read_text())
    changes = {item["cell"]: item["proposed_formula"] for item in manifest["change"]}
    checks.require_equal(
        changes,
        {
            "M1058": "=SUM(M1056)+$M1050",
            "O1058": "=SUM(O1056)+$O1050",
            "M1307": "=M1305+$M1299",
            "O1307": "=O1305+$O1299",
        },
    )
