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
    
    return logger

# 创建日志实例
logger = setup_logger('bilibili', 'bilibili.log')