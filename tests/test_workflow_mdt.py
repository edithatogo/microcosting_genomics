# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Exercise MDT attendance and case weighting."""

from fractions import Fraction

from genomics_microcosting.workflow_mdt import (
    Attendance,
    MeetingCase,
    MeetingObservation,
)
from tests import checks


def test_mdt_labour_uses_attendance_and_keeps_unknown() -> None:
    """Allocate known labour and preserve missing time for the second attendee."""
    meeting = MeetingObservation(
        elapsed_seconds=1800,
        attendance=(
            Attendance(attendee_id="a", role="scientist", seconds=1200),
            Attendance(attendee_id="b", role="clinician", seconds=None),
        ),
        cases=(
            MeetingCase(case_id="c1", weight=1),
            MeetingCase(case_id="c2", weight=2),
        ),
    )
    checks.require_equal(
        meeting.labour_seconds(),
        (
            ("a", "c1", Fraction(400)),
            ("a", "c2", Fraction(800)),
            ("b", "c1", None),
            ("b", "c2", None),
        ),
    )
