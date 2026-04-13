"""Checkpoint 存储管理器。

Per Review Fix #3: 大 JSON/markdown 不存数据库，存对象存储，
数据库只存路径引用。
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.storage import ObjectStorage
from app.utils.logger import logger


class CheckpointStore:
    """Checkpoint 存储管理器。

    将 parse_result、markdown、imrad 等大对象存到对象存储，
    数据库只存储引用路径。

    使用临时文件作为中间存储，适配 ObjectStorage 的文件上传/下载接口。
    """

    def __init__(self, storage: Optional[ObjectStorage] = None):
        """初始化 Checkpoint 存储。

        Args:
            storage: 对象存储实例，默认使用全局 storage
        """
        self.storage = storage or ObjectStorage()

    async def save_checkpoint(
        self,
        paper_id: str,
        stage: str,
        data: Dict[str, Any],
    ) -> str:
        """保存 checkpoint 到对象存储。

        Args:
            paper_id: 论文 ID
            stage: 当前阶段
            data: checkpoint 数据（parse_result, imrad, metadata 等）

        Returns:
            对象存储路径（存入 DB 的引用）
        """
        storage_key = f"checkpoints/{paper_id}/{stage}.json"

        # 序列化为 JSON
        json_data = json.dumps(data, ensure_ascii=False, indent=2)

        # 使用临时文件上传
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8"
        ) as tmp_file:
            tmp_file.write(json_data)
            tmp_path = tmp_file.name

        try:
            # 上传到对象存储
            await self.storage.upload_file(
                storage_key,
                tmp_path,
                content_type="application/json"
            )
            logger.debug(
                "Checkpoint saved",
                paper_id=paper_id,
                stage=stage,
                key=storage_key
            )
            return storage_key
        finally:
            # 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)

    async def load_checkpoint(
        self,
        storage_key: str,
    ) -> Optional[Dict[str, Any]]:
        """从对象存储加载 checkpoint。

        Args:
            storage_key: 对象存储路径

        Returns:
            checkpoint 数据，或 None 如果不存在
        """
        # 创建临时文件接收下载
        with tempfile.NamedTemporaryFile(
            suffix=".json",
            delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # 从对象存储下载
            await self.storage.download_file(storage_key, tmp_path)

            # 读取并解析 JSON
            with open(tmp_path, "r", encoding="utf-8") as f:
                json_data = f.read()
            return json.loads(json_data)
        except Exception as e:
            logger.warning(
                "Failed to load checkpoint",
                key=storage_key,
                error=str(e)
            )
            return None
        finally:
            # 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)

    async def delete_checkpoint(self, storage_key: str) -> None:
        """删除 checkpoint。

        Args:
            storage_key: 对象存储路径
        """
        await self.storage.delete_file(storage_key)
        logger.debug("Checkpoint deleted", key=storage_key)

    async def checkpoint_exists(self, storage_key: str) -> bool:
        """检查 checkpoint 是否存在。

        Args:
            storage_key: 对象存储路径

        Returns:
            True 如果存在
        """
        return await self.storage.file_exists(storage_key)