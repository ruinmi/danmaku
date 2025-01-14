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
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # 使用脚本所在目录作为日志文件的基准路径
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), log_file)

    file_handler = RotatingFileHandler(
        log_path, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # 将日志文件路径保存在 logger 对象上，供清空日志时使用
    logger.log_file_path = log_path

    return logger

def clear_log(logger):
    """清空日志文件（仅当文件大小超过 5MB 时）"""
    if hasattr(logger, 'log_file_path'):
        log_file_path = logger.log_file_path
        try:
            if os.path.exists(log_file_path) and os.path.getsize(log_file_path) > 5 * 1024 * 1024:
                with open(log_file_path, 'w', encoding='utf-8') as log_file:
                    log_file.truncate()  # 清空文件内容
                logger.info(f"日志文件 {log_file_path} 已清空，因为文件大小超过 5MB。")
            else:
                logger.info(f"日志文件 {log_file_path} 未超过 5MB，无需清空。")
        except Exception as e:
            logger.error(f"清空日志文件时发生错误: {e}")
    else:
        logger.warning("未找到日志文件路径，无法清空日志文件。")

# 创建日志实例
logger = setup_logger('bilibili', 'bilibili.log')