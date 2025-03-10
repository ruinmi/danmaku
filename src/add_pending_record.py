import time
from storage import Storage
from logger import logger
import os

def add_pending_record(title_keyword: str, after_timestamp: int = None):
    """
    添加待处理录播
    
    参数:
        title_keyword: 视频标题关键词
        after_timestamp: 起始时间戳，默认为当前时间
    """
    # 使用项目根目录下的config路径
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
    os.makedirs(config_dir, exist_ok=True)

    storage = Storage(os.path.join(config_dir, 'pending_records.json'))
    pending_list = storage.load()

    # 如果没有提供时间戳，使用当前时间
    if after_timestamp is None:
        after_timestamp = int(time.time())
    
        # 检查是否已存在相同的记录
        for video in pending_list:
            if video['title_keyword'] == title_keyword:
                logger.warning(f"已存在相同标题关键词的记录: {title_keyword}")
                return False
    else:
        after_timestamp = int(after_timestamp)
    
    # 添加新记录
    pending_list.append({
        'title_keyword': title_keyword,
        'after_timestamp': after_timestamp
    })
    
    # 保存到文件
    storage.save(pending_list)
    logger.info(f"成功添加待处理视频: {title_keyword}, 时间戳: {after_timestamp}")
    return True

def main():
    import sys
    import json
    
    # 从标准输入读取JSON数据
    data = json.load(sys.stdin)
    
    room_title = data.get('room_title', '').strip()
    after_timestamp = data.get('end_time', 0)
    
    # 检查room_title是否为空
    if not room_title:
        logger.error("房间标题为空，无法添加待处理记录")
        sys.exit(1)
        
    # 添加到待处理列表
    add_pending_record(room_title, after_timestamp)

if __name__ == "__main__":
    main() 