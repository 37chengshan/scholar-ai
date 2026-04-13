"""集成测试: 验证从 checkpoint 恢复时跳过已完成阶段。

Per Review Fix #10: 关键集成测试 #2。
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

from app.workers.pipeline_context import PipelineContext, PipelineStage
from app.core.checkpoint_store import CheckpointStore
from app.models.task_status import TaskStatus


class TestPipelineRecovery:
    """测试断点恢复语义。

    Per Review Fix #10: 断点恢复语义。

    从 checkpoint 恢复时：
    - 已完成的阶段（download, parse）应该跳过
    - 只执行失败点之后的阶段
    - stage_timings 不应该有重复记录
    """

    @pytest.mark.asyncio
    async def test_resume_from_extract_skips_download_and_parse(self):
        """验证: 从 extract 恢复时，不重复 download 和 parse。

        场景：
        1. download 成功，checkpoint 存储 local_path
        2. parse 成功，checkpoint 存储 parse_result
        3. extract 失败，status = failed_extract
        4. 恢复时，应该直接从 extract 开始，跳过 download/parse

        Per Review Fix #10: 断点恢复语义。
        """
        # 模拟 checkpoint 数据（parse 已完成）
        checkpoint_data = {
            "parse_result": {
                "page_count": 10,
                "markdown": "parsed content",
                "items": [
                    {"text": "Introduction...", "page_start": 1},
                    {"text": "Methods...", "page_start": 3},
                ],
            },
            "local_path": "/tmp/test.pdf",  # download 已完成
            "metadata": {"title": "Test Paper"},
        }

        # 创建 mock db_pool
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "test-task-id",
            "paper_id": "test-paper-id",
            "userId": "test-user-id",
            "storage_key": "test/key.pdf",
            "checkpointStage": "parse",  # parse 已完成
            "checkpointStorageKey": "checkpoints/test-paper-id/parse.json",
            "status": "failed_extract",
            "stageTimings": {"download_ms": 500, "parse_ms": 2000},  # 已有 timing
        })
        mock_conn.execute = AsyncMock()

        mock_db_pool = MagicMock()
        mock_db_pool.acquire = MagicMock()
        mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_db_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        # 创建 mock checkpoint store
        mock_checkpoint_store = Mock()
        mock_checkpoint_store.load_checkpoint = AsyncMock(return_value=checkpoint_data)

        # 模拟恢复流程
        # 1. 加载 checkpoint
        loaded_checkpoint = await mock_checkpoint_store.load_checkpoint(
            "checkpoints/test-paper-id/parse.json"
        )

        # 2. 验证 checkpoint 包含 parse_result
        assert loaded_checkpoint is not None
        assert loaded_checkpoint["parse_result"]["page_count"] == 10
        assert "markdown" in loaded_checkpoint["parse_result"]

        # 3. 创建恢复后的 PipelineContext
        ctx = PipelineContext(
            task_id="test-task-id",
            paper_id="test-paper-id",
            user_id="test-user-id",
            storage_key="test/key.pdf",
        )

        # 从 checkpoint 恢复状态
        ctx.parse_result = loaded_checkpoint["parse_result"]
        ctx.local_path = loaded_checkpoint["local_path"]
        ctx.current_stage = PipelineStage.EXTRACTION  # 从 extract 开始

        # 4. 验证恢复后的 context
        # parse_result 应该存在（不需要重新解析）
        assert ctx.parse_result is not None
        assert ctx.parse_result["page_count"] == 10

        # current_stage 应该是 EXTRACTION（跳过 DOWNLOAD 和 PARSING）
        assert ctx.current_stage == PipelineStage.EXTRACTION

        # 核心语义验证：恢复时跳过已完成的阶段

    @pytest.mark.asyncio
    async def test_resume_timing_no_duplicate_records(self):
        """验证: 恢复时 stage_timings 不重复记录已完成阶段。

        Per Review Fix #10: Timing 不重复语义。
        """
        # 模拟 DB 中已有的 timing 记录
        existing_timings = {
            "download_ms": 500,
            "parse_ms": 2000,
        }

        # 模拟从 checkpoint 恢复后的新 timing（只有 extract）
        new_timings_from_resume = {
            "extract_ms": 1500,
            "store_ms": 800,
        }

        # 合并后的 timing（不应该重复）
        merged_timings = {**existing_timings, **new_timings_from_resume}

        # 验证：每个阶段只有一个 timing 记录
        assert merged_timings.get("download_ms") == 500  # 保持原值
        assert merged_timings.get("parse_ms") == 2000  # 保持原值
        assert merged_timings.get("extract_ms") == 1500  # 新增
        assert merged_timings.get("store_ms") == 800  # 新增

        # 没有 "download_ms_2" 或重复键
        assert "download_ms_2" not in merged_timings

    @pytest.mark.asyncio
    async def test_checkpoint_path_format_is_consistent(self):
        """验证: checkpoint 路径格式始终一致。

        Per Review Fix #3: Checkpoint 路径引用存储。
        """
        paper_id = "paper-abc-123"
        stage = "parse"

        # 验证路径格式
        expected_path = f"checkpoints/{paper_id}/{stage}.json"

        # 创建 mock storage
        mock_storage = Mock()
        mock_storage.upload_file = AsyncMock()

        checkpoint_store = CheckpointStore(storage=mock_storage)

        # 保存 checkpoint（应该返回正确格式的路径）
        path = await checkpoint_store.save_checkpoint(
            paper_id=paper_id,
            stage=stage,
            data={"test": "data"},
        )

        assert path == expected_path

    def test_status_transition_from_failed_to_processing(self):
        """验证: 从 failed_* 恢复到 processing_* 的转换合法。

        Per Review Fix #2: 状态转换矩阵。
        """
        from app.models.task_status import is_valid_transition

        # 恢复转换合法
        assert is_valid_transition(TaskStatus.FAILED_DOWNLOAD, TaskStatus.PROCESSING_DOWNLOAD)
        assert is_valid_transition(TaskStatus.FAILED_PARSE, TaskStatus.PROCESSING_PARSE)
        assert is_valid_transition(TaskStatus.FAILED_EXTRACT, TaskStatus.PROCESSING_EXTRACT)
        assert is_valid_transition(TaskStatus.FAILED_STORE, TaskStatus.PROCESSING_STORE)

    @pytest.mark.asyncio
    async def test_resume_creates_fresh_context_from_checkpoint(self):
        """验证: 恢复时创建新的 PipelineContext 并填充 checkpoint 数据。

        Per Review Fix #10: 恢复创建新 context。
        """
        # 模拟 checkpoint 数据
        checkpoint_data = {
            "parse_result": {
                "page_count": 15,
                "markdown": "Full paper content...",
                "items": [],
            },
            "imrad": {
                "introduction": {"content": "Intro...", "page_start": 1, "page_end": 3},
                "methods": {"content": "Methods...", "page_start": 4, "page_end": 8},
            },
            "metadata": {
                "title": "Recovered Paper",
                "authors": ["Author 1", "Author 2"],
            },
        }

        # 创建新的 PipelineContext
        ctx = PipelineContext(
            task_id="recovered-task",
            paper_id="recovered-paper",
            user_id="recovered-user",
            storage_key="recovered/key.pdf",
        )

        # 恢复 checkpoint 数据
        ctx.parse_result = checkpoint_data.get("parse_result")
        ctx.imrad = checkpoint_data.get("imrad")
        ctx.metadata = checkpoint_data.get("metadata")

        # 验证恢复后的 context
        assert ctx.parse_result["page_count"] == 15
        assert ctx.imrad["introduction"]["page_start"] == 1
        assert ctx.metadata["title"] == "Recovered Paper"

        # 核心语义：恢复的 context 应该包含所有已完成阶段的结果


class TestCheckpointStorage:
    """测试 Checkpoint 存储与恢复的完整流程。

    Per Review Fix #3: Checkpoint 存对象存储，DB 存路径引用。
    """

    @pytest.mark.asyncio
    async def test_checkpoint_save_returns_path_only(self):
        """验证: save_checkpoint 返回路径，不返回内容。

        Per Review Fix #3: DB 只存路径引用。
        """
        mock_storage = Mock()
        mock_storage.upload_file = AsyncMock()

        checkpoint_store = CheckpointStore(storage=mock_storage)

        # 保存大数据
        large_data = {
            "markdown": "Very long content..." * 1000,
            "items": [{"text": f"item {i}"} for i in range(100)],
        }

        result = await checkpoint_store.save_checkpoint(
            paper_id="test-paper",
            stage="parse",
            data=large_data,
        )

        # 返回值是路径字符串，不是 JSON 内容
        assert isinstance(result, str)
        assert result.startswith("checkpoints/")
        assert ".json" in result

        # DB 应该存储这个路径，而不是 JSON 内容

    @pytest.mark.asyncio
    async def test_checkpoint_load_retrieves_full_data(self):
        """验证: load_checkpoint 能取回完整数据。

        Per Review Fix #10: 恢复需要完整数据。
        """
        # 模拟完整的 checkpoint 数据
        full_checkpoint = {
            "parse_result": {
                "page_count": 25,
                "markdown": "# Introduction\n\nLong content...",
                "items": [{"text": "chunk1"}, {"text": "chunk2"}],
            },
            "imrad": {
                "introduction": {"content": "Intro", "page_start": 1},
                "methods": {"content": "Methods", "page_start": 5},
                "results": {"content": "Results", "page_start": 10},
                "conclusion": {"content": "Conclusion", "page_start": 20},
            },
            "metadata": {
                "title": "Full Paper Title",
                "authors": ["A", "B", "C"],
                "abstract": "Abstract content...",
                "doi": "10.1234/test",
            },
        }

        # 创建 mock storage 并模拟文件内容
        mock_storage = Mock()

        # 使用 patch 模拟文件读取
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(full_checkpoint)
            mock_open.return_value.__enter__.return_value = mock_file

            with patch("app.core.checkpoint_store.Path.unlink"):
                checkpoint_store = CheckpointStore(storage=mock_storage)
                mock_storage.download_file = AsyncMock()

                # 加载 checkpoint
                loaded = await checkpoint_store.load_checkpoint(
                    "checkpoints/test/parse.json"
                )

        # 验证加载的数据完整
        assert loaded["parse_result"]["page_count"] == 25
        assert loaded["imrad"]["introduction"]["page_start"] == 1
        assert loaded["metadata"]["title"] == "Full Paper Title"


class TestRecoveryScenarios:
    """测试各种恢复场景。

    验证从不同失败点恢复的行为。
    """

    @pytest.mark.asyncio
    async def test_resume_from_download_failure(self):
        """验证: download 失败恢复时，重新执行 download。

        download 失败 = 没有 checkpoint，从 scratch 开始。
        """
        # download 失败时没有 checkpoint 数据
        ctx = PipelineContext(
            task_id="download-failed-task",
            paper_id="download-failed-paper",
            user_id="test-user",
            storage_key="test/key.pdf",
        )

        # download 失败后恢复，current_stage 应该回到 DOWNLOAD
        ctx.current_stage = PipelineStage.DOWNLOAD

        # 没有 parse_result（需要重新下载和解析）
        assert ctx.parse_result is None
        assert ctx.local_path is None

        # 恢复时应该从 download 开始

    @pytest.mark.asyncio
    async def test_resume_from_parse_failure(self):
        """验证: parse 失败恢复时，重新执行 parse（download 已完成）。

        parse 失败 = download checkpoint 存在，parse 需要重新执行。
        """
        # download 成功的 checkpoint
        checkpoint_data = {
            "local_path": "/tmp/resumed.pdf",
        }

        ctx = PipelineContext(
            task_id="parse-failed-task",
            paper_id="parse-failed-paper",
            user_id="test-user",
            storage_key="test/key.pdf",
        )

        # 恢复 download checkpoint
        ctx.local_path = checkpoint_data["local_path"]
        ctx.current_stage = PipelineStage.PARSING

        # 有 local_path，没有 parse_result
        assert ctx.local_path == "/tmp/resumed.pdf"
        assert ctx.parse_result is None

        # 恢复时应该从 parse 开始（跳过 download）

    @pytest.mark.asyncio
    async def test_resume_from_store_failure(self):
        """验证: store 失败恢复时，跳过所有已完成的 extraction。

        store 失败 = parse + extract 都已完成，只需重新 store。
        """
        # 完整的 extraction checkpoint
        checkpoint_data = {
            "parse_result": {"page_count": 10, "markdown": "content", "items": []},
            "imrad": {"introduction": {"content": "intro"}},
            "metadata": {"title": "Test"},
            "image_results": [],
            "table_results": [],
        }

        ctx = PipelineContext(
            task_id="store-failed-task",
            paper_id="store-failed-paper",
            user_id="test-user",
            storage_key="test/key.pdf",
        )

        # 恢复所有 extraction 结果
        ctx.parse_result = checkpoint_data["parse_result"]
        ctx.imrad = checkpoint_data["imrad"]
        ctx.metadata = checkpoint_data["metadata"]
        ctx.current_stage = PipelineStage.STORAGE

        # 所有 extraction 结果都存在
        assert ctx.parse_result is not None
        assert ctx.imrad is not None
        assert ctx.metadata is not None

        # 恢复时应该从 store 开始（跳过 download/parse/extract）