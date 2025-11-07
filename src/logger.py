import logging
from logging.handlers import RotatingFileHandler
import sys
import os

def setup_logger(name: str, log_file: str, level=logging.INFO):
    """配置日志"""
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 确定日志路径
    log_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        log_file
    )

    # 避免重复添加 handler
    _logger = logging.getLogger(name)
    if _logger.handlers:
        return _logger  # 已经配置过，直接返回

    _logger.setLevel(level)
    _logger.propagate = False  # 避免日志被上层 logger 再处理一次

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    _logger.addHandler(console_handler)

    # 文件输出
    file_handler = RotatingFileHandler(
        log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    _logger.addHandler(file_handler)

    # 保存日志文件路径（供 clear_log 使用）
    _logger.log_file_path = log_path

    return _logger

def clear_log(__logger):
    """清空日志文件（仅当文件大小超过 5MB 时）"""
    if hasattr(__logger, 'log_file_path'):
        log_file_path = __logger.log_file_path
        try:
            if os.path.exists(log_file_path) and os.path.getsize(log_file_path) > 5 * 1024 * 1024:
                with open(log_file_path, 'w', encoding='utf-8') as log_file:
                    log_file.truncate()  # 清空文件内容
                __logger.info(f"日志文件 {log_file_path} 已清空，因为文件大小超过 5MB。")
        except Exception as e:
            __logger.error(f"清空日志文件时发生错误: {e}")
    else:
        __logger.warning("未找到日志文件路径，无法清空日志文件。")

# 创建日志实例
logger = setup_logger('bilibili', 'bilibili.log')
