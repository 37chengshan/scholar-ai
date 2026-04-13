"""阶段计时工具 - 使用 monotonic 防止系统时间调整影响。

Per Review Fix #6: time.monotonic() + mock time 测试。
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable


@dataclass
class StageTimer:
    """阶段计时器。

    使用 time.monotonic() 而不是 time.time()，
    遅免系统时钟调整影响计时准确性。
    """
    stages: Dict[str, int] = field(default_factory=dict)  # stage -> duration_ms
    current_stage: Optional[str] = None
    start_monotonic: Optional[float] = None

    # Per Review Fix #6: 支持注入时间源（便于测试）
    # 使用 None 作为默认值，在 __post_init__ 中设置实际时间源
    _time_source: Optional[Callable[[], float]] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """初始化时间源。"""
        if self._time_source is None:
            self._time_source = time.monotonic

    def start(self, stage: str) -> None:
        """开始阶段计时。"""
        self.current_stage = stage
        self.start_monotonic = self._time_source()

    def end(self) -> int:
        """结束当前阶段，返回毫秒数。"""
        # 使用 is not None 检查，避免 0.0 被误判为 False
        if self.current_stage is not None and self.start_monotonic is not None:
            elapsed = self._time_source() - self.start_monotonic
            duration_ms = round(elapsed * 1000)
            self.stages[self.current_stage] = duration_ms
            self.current_stage = None
            self.start_monotonic = None
            return duration_ms
        return 0

    def get_all(self) -> Dict[str, int]:
        """获取所有阶段耗时。"""
        return self.stages.copy()

    def get_total(self) -> int:
        """获取总耗时。"""
        return sum(self.stages.values())

    def to_json(self) -> Dict[str, int]:
        """导出为 JSON 格式（用于存储）。"""
        return {
            f"{stage}_ms": duration
            for stage, duration in self.stages.items()
        } | {"total_ms": self.get_total()}