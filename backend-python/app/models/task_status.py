"""ProcessingTask 状态枚举 + 合法转换验证。

Per Review Fix #2, #7: 状态映射表 + 统一 vocabulary。
"""

from enum import Enum
from typing import Set, Tuple


class TaskStatus(str, Enum):
    """ProcessingTask 状态（统一 vocabulary）。

    Vocabulary: download/parse/extract/store/notes
    """
    # 初始
    UPLOADED = "uploaded"
    QUEUED = "queued"

    # 处理中
    PROCESSING_DOWNLOAD = "processing_download"
    PROCESSING_PARSE = "processing_parse"
    PROCESSING_EXTRACT = "processing_extract"
    PROCESSING_STORE = "processing_store"

    # 终态成功
    READY = "ready"        # 主链完成
    COMPLETED = "completed"  # 全部完成

    # 终态失败
    FAILED_DOWNLOAD = "failed_download"
    FAILED_PARSE = "failed_parse"
    FAILED_EXTRACT = "failed_extract"
    FAILED_STORE = "failed_store"

    # 部分失败
    PARTIAL_FAILED = "partial_failed"


# 合法转换矩阵
VALID_TRANSITIONS: Set[Tuple[TaskStatus, TaskStatus]] = {
    # 主线流程
    (TaskStatus.UPLOADED, TaskStatus.QUEUED),
    (TaskStatus.QUEUED, TaskStatus.PROCESSING_DOWNLOAD),
    (TaskStatus.PROCESSING_DOWNLOAD, TaskStatus.PROCESSING_PARSE),
    (TaskStatus.PROCESSING_PARSE, TaskStatus.PROCESSING_EXTRACT),
    (TaskStatus.PROCESSING_EXTRACT, TaskStatus.PROCESSING_STORE),
    (TaskStatus.PROCESSING_STORE, TaskStatus.READY),
    (TaskStatus.READY, TaskStatus.COMPLETED),

    # 失败分支
    (TaskStatus.PROCESSING_DOWNLOAD, TaskStatus.FAILED_DOWNLOAD),
    (TaskStatus.PROCESSING_PARSE, TaskStatus.FAILED_PARSE),
    (TaskStatus.PROCESSING_EXTRACT, TaskStatus.FAILED_EXTRACT),
    (TaskStatus.PROCESSING_STORE, TaskStatus.FAILED_STORE),

    # 恢复分支
    (TaskStatus.FAILED_DOWNLOAD, TaskStatus.PROCESSING_DOWNLOAD),
    (TaskStatus.FAILED_PARSE, TaskStatus.PROCESSING_PARSE),
    (TaskStatus.FAILED_EXTRACT, TaskStatus.PROCESSING_EXTRACT),
    (TaskStatus.FAILED_STORE, TaskStatus.PROCESSING_STORE),

    # 部分失败
    (TaskStatus.READY, TaskStatus.PARTIAL_FAILED),
}


def is_valid_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    """验证状态转换是否合法。"""
    return (from_status, to_status) in VALID_TRANSITIONS


def validate_transition(from_status: TaskStatus, to_status: TaskStatus) -> None:
    """验证转换，非法时抛异常。"""
    if not is_valid_transition(from_status, to_status):
        raise ValueError(
            f"Invalid status transition: {from_status.value} → {to_status.value}"
        )