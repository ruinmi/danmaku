from typing import Dict
import time
from logger import logger, clear_log
from src.config import config
from storage import Storage
from api import get_video_parts, auto_send_danmaku, check_up_latest_video, send_danmaku
import os

class VideoMonitor:
    def __init__(self, config: Dict):
        self.config = config
        # 使用项目根目录下的config路径
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
        os.makedirs(config_dir, exist_ok=True)
        
        self.storage = Storage(os.path.join(config_dir, 'pending_records.json'))
        
    def check_pending_videos(self):
        # 读取当前的待处理列表
        pending_list = self.storage.load()
        if not pending_list:
            return
            
        processed_videos = []  # 记录已处理的视频
            
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

                total_earnings = 0
                for index, (cid, part, duration) in enumerate(parts):
                    xml_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'danmaku', f"{part}.xml")
                    if not os.path.exists(xml_file):
                        logger.warning(f"XML文件不存在: {xml_file}")
                        continue

                    total_earnings += auto_send_danmaku(
                        xml_path=xml_file,
                        video_cid=cid,
                        video_duration=duration,
                        bvid=bvid
                    )
                    # 发送完成后删除XML文件
                    os.remove(xml_file)
                    logger.info(f"已删除XML文件: {xml_file}")
                    if index == len(parts)-1:
                        acc = config.bilibili['accounts'][0]
                        success, message, _ = send_danmaku(cid, f'Earned {total_earnings}', bvid, 0, 16646914,acc['csrf'], acc['sessdata'])
                        if not success:
                            logger.warning(f"发送主播收益失败, 消息: {message}")


                # 记录已处理的视频
                processed_videos.append(video)
                logger.info(f"视频 {video['title_keyword']} 处理完成")
                
            except Exception as e:
                logger.error(f"处理视频失败: {str(e)}", exc_info=True)
        
        if processed_videos:
            # 重新读取最新的待处理列表
            current_pending_list = self.storage.load()
            # 从最新列表中移除已处理的视频
            for video in processed_videos:
                for pending_video in current_pending_list[:]:
                    if (pending_video['title_keyword'] == video['title_keyword'] and 
                        pending_video['after_timestamp'] == video['after_timestamp']):
                        current_pending_list.remove(pending_video)
            
            # 保存更新后的列表
            self.storage.save(current_pending_list)
    
    def monitor(self):
        logger.info("开始监控")
        while True:
            try:
                clear_log(logger)
                self.check_pending_videos()
                time.sleep(self.config['interval'])
            except KeyboardInterrupt:
                logger.info("监控已停止")
                break
            except Exception as e:
                logger.error(f"监控发生错误: {str(e)}")
                time.sleep(self.config['retry_delay']) 
