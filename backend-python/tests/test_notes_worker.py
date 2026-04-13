"""Tests for NotesWorker with claim lock mechanism.

Per Review Fix #9: 验证 FOR UPDATE SKIP LOCKED 抢占机制。
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.workers.notes_worker import NotesWorker


class TestNotesWorkerClaim:
    """测试 NotesWorker 抢占机制。"""

    @pytest.mark.asyncio
    async def test_claim_task_uses_skip_locked(self):
        """验证抢占使用 FOR UPDATE SKIP LOCKED（Per Review Fix #9）。"""
        worker = NotesWorker()

        # Mock db_pool
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            return_value={
                "id": "task-123",
                "paper_id": "paper-456",
                "status": "claimed",
                "claimed_by": worker.WORKER_ID,
                "claimed_at": "2024-01-01T00:00:00Z",
            }
        )

        # Mock async context manager for pool.acquire()
        mock_acquire = AsyncMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=None)

        worker.db_pool = Mock()
        worker.db_pool.acquire = Mock(return_value=mock_acquire)

        task = await worker.claim_task()

        # 验证 SQL 包含 FOR UPDATE SKIP LOCKED
        call_args = mock_conn.fetchrow.call_args[0]
        sql = call_args[0]
        assert "FOR UPDATE SKIP LOCKED" in sql

        assert task["id"] == "task-123"
        assert task["status"] == "claimed"
        assert task["claimed_by"] == worker.WORKER_ID

    @pytest.mark.asyncio
    async def test_claim_task_returns_none_when_no_pending_tasks(self):
        """验证无任务时返回 None。"""
        worker = NotesWorker()

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        mock_acquire = AsyncMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=None)

        worker.db_pool = Mock()
        worker.db_pool.acquire = Mock(return_value=mock_acquire)

        task = await worker.claim_task()

        assert task is None

    @pytest.mark.asyncio
    async def test_complete_task_updates_paper_is_notes_ready(self):
        """验证完成时更新 Paper.isNotesReady。"""
        worker = NotesWorker()

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        mock_acquire = AsyncMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=None)

        worker.db_pool = Mock()
        worker.db_pool.acquire = Mock(return_value=mock_acquire)

        await worker.complete_task("task-123", "paper-456", "test notes")

        # 验证 execute 被调用两次（Paper 更新 + NotesTask 更新）
        assert mock_conn.execute.call_count == 2

        # 验证第一个调用包含 isNotesReady = TRUE
        first_call_args = mock_conn.execute.call_args_list[0][0]
        sql = first_call_args[0]
        assert '"isNotesReady"' in sql or 'isNotesReady' in sql

    @pytest.mark.asyncio
    async def test_fail_task_increments_attempts(self):
        """验证失败时增加 attempts 并自动重试。"""
        worker = NotesWorker()

        mock_conn = AsyncMock()
        # Return attempts after increment (simulate attempts becoming 2)
        mock_conn.fetchrow = AsyncMock(return_value={"attempts": 2})

        mock_acquire = AsyncMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=None)

        worker.db_pool = Mock()
        worker.db_pool.acquire = Mock(return_value=mock_acquire)

        # Mock reset_for_retry
        worker.reset_for_retry = AsyncMock(return_value=True)

        result = await worker.fail_task("task-123", "Some error message")

        # 验证 fetchrow 被调用（用于 increment + returning）
        assert mock_conn.fetchrow.call_count == 1

        # 验证 SQL 包含 attempts = attempts + 1
        call_args = mock_conn.fetchrow.call_args[0]
        sql = call_args[0]
        assert "attempts = attempts + 1" in sql

        # 验证自动重试被调用（因为 attempts=2 < MAX_ATTEMPTS=3）
        worker.reset_for_retry.assert_called_once_with("task-123")

        # 验证返回 True（表示已重置）
        assert result is True

    @pytest.mark.asyncio
    async def test_fail_task_truncates_long_error_message(self):
        """验证长错误消息被截断到 500 字符。"""
        worker = NotesWorker()

        mock_conn = AsyncMock()
        # Return attempts >= MAX_ATTEMPTS to prevent auto-retry
        mock_conn.fetchrow = AsyncMock(return_value={"attempts": 3})

        mock_acquire = AsyncMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=None)

        worker.db_pool = Mock()
        worker.db_pool.acquire = Mock(return_value=mock_acquire)

        # Mock reset_for_retry (won't be called since attempts >= MAX_ATTEMPTS)
        worker.reset_for_retry = AsyncMock(return_value=False)

        long_error = "x" * 1000
        result = await worker.fail_task("task-123", long_error)

        # 验证错误消息被截断
        call_args = mock_conn.fetchrow.call_args[0]
        error_arg = call_args[1]
        assert len(error_arg) == 500

        # 验证返回 False（表示未重置，永久失败）
        assert result is False

    @pytest.mark.asyncio
    async def test_reset_for_retry_returns_true_when_under_max_attempts(self):
        """验证重试次数未达上限时可以重置。"""
        worker = NotesWorker()

        mock_conn = AsyncMock()
        # First call: fetchrow to get attempts
        # Second call: execute to reset
        mock_conn.fetchrow = AsyncMock(return_value={"attempts": 2})
        mock_conn.execute = AsyncMock()

        mock_acquire = AsyncMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=None)

        worker.db_pool = Mock()
        worker.db_pool.acquire = Mock(return_value=mock_acquire)

        result = await worker.reset_for_retry("task-123")

        # 验证返回 True（可以重试）
        assert result is True

        # 验证 execute 被调用进行重置
        assert mock_conn.execute.call_count == 1

        # 验证 SQL 设置 status = 'pending'
        call_args = mock_conn.execute.call_args[0]
        sql = call_args[0]
        assert "status = 'pending'" in sql
        assert "claimed_by = NULL" in sql

    @pytest.mark.asyncio
    async def test_reset_for_retry_returns_false_when_max_attempts_exceeded(self):
        """验证重试次数已达上限时不能重置。"""
        worker = NotesWorker()

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"attempts": 3})
        mock_conn.execute = AsyncMock()

        mock_acquire = AsyncMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=None)

        worker.db_pool = Mock()
        worker.db_pool.acquire = Mock(return_value=mock_acquire)

        result = await worker.reset_for_retry("task-123")

        # 验证返回 False（不能重试）
        assert result is False

        # 验证 execute 未被调用
        assert mock_conn.execute.call_count == 0


class TestNotesWorkerGenerate:
    """测试 NotesWorker 笔记生成。"""

    @pytest.mark.asyncio
    async def test_generate_notes_calls_notes_generator(self):
        """验证调用 NotesGenerator.generate_notes。"""
        worker = NotesWorker()

        # Mock db_pool for paper fetch
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            return_value={
                "title": "Test Paper",
                "authors": ["Author 1"],
                "year": 2024,
                "venue": "Test Venue",
                "imradJson": {"introduction": {"content": "Intro"}},
            }
        )

        mock_acquire = AsyncMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=None)

        worker.db_pool = Mock()
        worker.db_pool.acquire = Mock(return_value=mock_acquire)

        # Mock NotesGenerator
        with patch.object(
            worker.notes_generator,
            "generate_notes",
            AsyncMock(return_value="# Generated Notes"),
        ) as mock_generate:
            notes = await worker.generate_notes("paper-456")

            assert notes == "# Generated Notes"
            mock_generate.assert_called_once()

            # 验证传入的参数
            call_kwargs = mock_generate.call_args[1]
            assert call_kwargs["paper_metadata"]["title"] == "Test Paper"
            assert call_kwargs["imrad_structure"]["introduction"]["content"] == "Intro"

    @pytest.mark.asyncio
    async def test_generate_notes_returns_none_for_missing_paper(self):
        """验证论文不存在时返回 None。"""
        worker = NotesWorker()

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        mock_acquire = AsyncMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=None)

        worker.db_pool = Mock()
        worker.db_pool.acquire = Mock(return_value=mock_acquire)

        notes = await worker.generate_notes("nonexistent-paper")

        assert notes is None


class TestNotesWorkerShutdown:
    """测试 NotesWorker 关闭。"""

    @pytest.mark.asyncio
    async def test_shutdown_closes_pool(self):
        """验证关闭时关闭连接池。"""
        worker = NotesWorker()

        mock_pool = AsyncMock()
        mock_pool.close = AsyncMock()
        worker.db_pool = mock_pool

        await worker.shutdown()

        mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_handles_no_pool(self):
        """验证无连接池时正常处理。"""
        worker = NotesWorker()
        worker.db_pool = None

        await worker.shutdown()  # Should not raise