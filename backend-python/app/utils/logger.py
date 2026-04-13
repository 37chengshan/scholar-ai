"""日志工具

Per Review Fix #8: 全链路 trace 追踪。
"""

import logging
import os
import structlog


# 配置 structlog (compatible with structlog 25.x)
# merge_contextvars processor automatically adds all bound contextvars to event dict
# Including: trace_id, paper_id, task_id (when bound via bind_contextvars)
structlog.configure(
    processors=[
        # 自动合并 contextvars 到日志事件
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
        if os.getenv("LOG_FORMAT") == "console"
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(os.getenv("LOG_LEVEL", "INFO"))
    ),
)

logger = structlog.get_logger()