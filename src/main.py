from config import config
from logger import logger
from monitor import VideoMonitor

def main():
    monitor = VideoMonitor(config.monitor)
    try:
        monitor.monitor()
    except Exception as e:
        logger.error(f"程序异常退出: {str(e)}")

if __name__ == "__main__":
    main()
