import pytest
from app.core.timing import StageTimer


class TestStageTimer:
    """测试阶段计时器（mock time，不 sleep）。"""

    def test_start_end_with_mock_time(self):
        """使用 mock 时间源测试，避免真实 sleep。"""
        # Mock 时间源：第一次返回 0，第二次返回 0.1（100ms）
        mock_times = [0.0, 0.1]
        timer = StageTimer(_time_source=lambda: mock_times.pop(0))

        timer.start("download")
        elapsed = timer.end()

        assert elapsed == 100  # 100ms
        assert timer.stages["download"] == 100
        assert len(mock_times) == 0  # 时间源被调用两次

    def test_multiple_stages(self):
        """测试多阶段计时。"""
        mock_times = [0.0, 0.05, 0.05, 0.15]  # download 50ms, parse 100ms
        timer = StageTimer(_time_source=lambda: mock_times.pop(0))

        timer.start("download")
        timer.end()

        timer.start("parse")
        timer.end()

        assert timer.stages["download"] == 50
        assert timer.stages["parse"] == 100
        assert timer.get_total() == 150

    def test_to_json_format(self):
        """测试 JSON 输出格式。"""
        timer = StageTimer()
        timer.stages = {"download": 100, "parse": 200}

        json_out = timer.to_json()
        assert json_out["download_ms"] == 100
        assert json_out["parse_ms"] == 200
        assert json_out["total_ms"] == 300

    def test_no_real_sleep(self):
        """验证测试不依赖真实 sleep（快速执行）。"""
        import time
        start = time.monotonic()

        # 运行 1000 次测试（应该 < 1s）
        for _ in range(1000):
            mock_times = [0.0, 0.1]
            timer = StageTimer(_time_source=lambda: mock_times.pop(0))
            timer.start("test")
            timer.end()

        elapsed = time.monotonic() - start
        assert elapsed < 1.0  # 1000 次测试应该在 1 秒内完成