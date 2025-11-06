import inspect
import logging
import os
import sys

from loguru import logger

from backend.core.conf import settings
from backend.core.path_conf import LOG_DIR


class InterceptHandler(logging.Handler):
    """
    日志拦截处理器，用于将标准库的日志重定向到 loguru

    参考：https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """
    def emit(self, record: logging.LogRecord):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    """配置日志处理器


    """
    # 设置根日志处理器和等级
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(settings.LOG_STD_LEVEL)

    # 配置日志传播规则
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        if "unicorn.access" in name or "watchfiles.main" in name:
            logging.getLogger(name).propagate = False
        else:
            logging.getLogger(name).propagate = True

    logger.remove()
    logger.configure(
       handlers=[
           {
               "sink": sys.stdout,
               "level": settings.LOG_STD_LEVEL,
               "format": settings.LOG_STD_FORMAT,
           }
       ]
    )


def set_custom_logfile():
    """配置自定义日志文件"""

    log_path = LOG_DIR
    if not os.path.exists(log_path):
        os.makedirs(log_path)

    # 日志文件
    log_access_file = os.path.join(log_path, settings.LOG_ACCESS_FILENAME)
    log_error_file = os.path.join(log_path, settings.LOG_ERROR_FILENAME)

    # 日志文件通用配置
    # https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.add
    log_config = {
        'format': settings.LOG_FILE_FORMAT,
        'enqueue': True,
        'rotation': '5 MB',
        'retention': '7 days',
        'compression': 'tar.gz',
    }

    # 标准输出文件
    logger.add(
        str(log_access_file),
        level=settings.LOG_ACCESS_FILE_LEVEL,
        filter=lambda record: record['level'].no <= 25,
        backtrace=False,
        diagnose=False,
        **log_config,
    )

    # 标准错误文件
    logger.add(
        str(log_error_file),
        level=settings.LOG_ERROR_FILE_LEVEL,
        filter=lambda record: record['level'].no >= 30,
        backtrace=True,
        diagnose=True,
        **log_config,
    )


log = logger
