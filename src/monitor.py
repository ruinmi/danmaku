from typing import Dict
import time
from logger import logger
from storage import Storage
from api import get_video_parts, auto_send_danmaku, check_up_latest_video
import os

class VideoMonitor:
    def __init__(self, config: Dict):
        self.config = config
        # 使用项目根目录下的config路径
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
        os.makedirs(config_dir, exist_ok=True)
        
        self.storage = Storage(os.path.join(config_dir, 'pending_records.json'))        
    def check_pending_videos(self):
        pending_list = self.storage.load()
        if not pending_list:
            return
            
        for video in pending_list[:]:  # 使用切片创建副本以便修改
            try:
                # 检查视频是否已发布
                bvid = check_up_latest_video(
                    mid=self.config['mid'],
                    title_keyword=video['title_keyword'],
                    after_timestamp=video['after_timestamp']
                )
                
                if not bvid:
                    continue
                    
                logger.info(f"视频已发布: {video['title_keyword']} - {bvid}")
                # 获取视频分P信息并发送弹幕
                parts = get_video_parts(bvid)
                
                for cid, part in parts:
                    xml_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'danmaku', f"{part}.xml")
                    if not os.path.exists(xml_file):
                        logger.warning(f"XML文件不存在: {xml_file}")
                        continue
                        
                    auto_send_danmaku(
                        xml_path=xml_file,
                        video_cid=cid,
                        bvid=bvid
                    )
                    # 发送完成后删除XML文件
                    os.remove(xml_file)
                    logger.info(f"已删除XML文件: {xml_file}")
                # 处理完成后从列表中移除
                pending_list.remove(video)
                logger.info(f"视频 {video['title_keyword']} 处理完成")
                
            except Exception as e:
                logger.error(f"处理视频失败: {str(e)}")
                
        self.storage.save(pending_list)
    
    def monitor(self):
        logger.info("开始监控")
        while True:
            try:
                self.check_pending_videos()
                time.sleep(self.config['interval'])
            except KeyboardInterrupt:
                logger.info("监控已停止")
                break
            except Exception as e:
                logger.error(f"监控发生错误: {str(e)}")
                time.sleep(self.config['retry_delay']) 