from app.core.observability.context import (
    bind_optional_context,
    clear_context,
    current_context_dict,
    set_request_context,
    set_run_context,
)


def test_set_request_context_and_current_context_dict():
    clear_context()
    set_request_context(request_id="req-1", route="/api/v1/rag/query", user_id="user-1")

    context = current_context_dict()

    assert context["request_id"] == "req-1"
    assert context["route"] == "/api/v1/rag/query"
    assert context["user_id"] == "user-1"


def test_set_run_context_and_bind_optional_context():
    clear_context()
    set_run_context(run_id="run-1", session_id="sess-1", message_id="msg-1")
    bind_optional_context(job_id="job-1", kb_id="kb-1")

    context = current_context_dict()

    assert context["run_id"] == "run-1"
    assert context["session_id"] == "sess-1"
    assert context["message_id"] == "msg-1"
    assert context["job_id"] == "job-1"
    assert context["kb_id"] == "kb-1"


def test_clear_context_resets_all_fields():
    set_request_context(request_id="req-clear")
    set_run_context(run_id="run-clear")
    clear_context()

    context = current_context_dict()

    assert context == {}
