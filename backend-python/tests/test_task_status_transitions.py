import pytest
from app.models.task_status import (
    TaskStatus,
    is_valid_transition,
    validate_transition,
    VALID_TRANSITIONS,
)


class TestValidTransitions:
    """测试合法状态转换。"""

    def test_main_flow_transitions(self):
        """验证主线流程转换合法。"""
        assert is_valid_transition(TaskStatus.UPLOADED, TaskStatus.QUEUED)
        assert is_valid_transition(TaskStatus.QUEUED, TaskStatus.PROCESSING_DOWNLOAD)
        assert is_valid_transition(TaskStatus.PROCESSING_DOWNLOAD, TaskStatus.PROCESSING_PARSE)
        assert is_valid_transition(TaskStatus.PROCESSING_PARSE, TaskStatus.PROCESSING_EXTRACT)
        assert is_valid_transition(TaskStatus.PROCESSING_EXTRACT, TaskStatus.PROCESSING_STORE)
        assert is_valid_transition(TaskStatus.PROCESSING_STORE, TaskStatus.READY)
        assert is_valid_transition(TaskStatus.READY, TaskStatus.COMPLETED)

    def test_failure_branches(self):
        """验证失败分支合法。"""
        assert is_valid_transition(TaskStatus.PROCESSING_DOWNLOAD, TaskStatus.FAILED_DOWNLOAD)
        assert is_valid_transition(TaskStatus.PROCESSING_PARSE, TaskStatus.FAILED_PARSE)
        assert is_valid_transition(TaskStatus.PROCESSING_EXTRACT, TaskStatus.FAILED_EXTRACT)
        assert is_valid_transition(TaskStatus.PROCESSING_STORE, TaskStatus.FAILED_STORE)

    def test_recovery_branches(self):
        """验证恢复分支合法。"""
        assert is_valid_transition(TaskStatus.FAILED_DOWNLOAD, TaskStatus.PROCESSING_DOWNLOAD)
        assert is_valid_transition(TaskStatus.FAILED_PARSE, TaskStatus.PROCESSING_PARSE)


class TestInvalidTransitions:
    """测试非法状态转换（Per Review Fix #2）。"""

    def test_jump_to_completed(self):
        """禁止 queued → completed 跳跃。"""
        assert not is_valid_transition(TaskStatus.QUEUED, TaskStatus.COMPLETED)
        with pytest.raises(ValueError, match="Invalid status transition"):
            validate_transition(TaskStatus.QUEUED, TaskStatus.COMPLETED)

    def test_jump_to_ready_from_parse(self):
        """禁止 processing_parse → ready 跳跃。"""
        assert not is_valid_transition(TaskStatus.PROCESSING_PARSE, TaskStatus.READY)
        with pytest.raises(ValueError):
            validate_transition(TaskStatus.PROCESSING_PARSE, TaskStatus.READY)

    def test_backwards_from_ready(self):
        """禁止 ready → processing_* 回退。"""
        assert not is_valid_transition(TaskStatus.READY, TaskStatus.PROCESSING_PARSE)
        with pytest.raises(ValueError):
            validate_transition(TaskStatus.READY, TaskStatus.PROCESSING_PARSE)

    def test_failed_to_completed(self):
        """禁止 failed_* → completed 直接完成。"""
        assert not is_valid_transition(TaskStatus.FAILED_PARSE, TaskStatus.COMPLETED)
        with pytest.raises(ValueError):
            validate_transition(TaskStatus.FAILED_PARSE, TaskStatus.COMPLETED)