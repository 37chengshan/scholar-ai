import pytest

from app.services.import_job_service import ImportJobService


@pytest.mark.parametrize(
    "current,target,valid",
    [
        ("created", "queued", True),
        ("queued", "running", True),
        ("running", "completed", True),
        ("awaiting_user_action", "running", True),
        ("completed", "running", False),
        ("cancelled", "running", False),
        ("created", "completed", False),
    ],
)
def test_import_job_transition_guard(current: str, target: str, valid: bool):
    service = ImportJobService()

    if valid:
        service._validate_status_transition(current, target)
    else:
        with pytest.raises(ValueError, match="Invalid transition"):
            service._validate_status_transition(current, target)
