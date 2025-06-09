import requests
import time
import hashlib
from typing import List, Tuple
import xml.etree.ElementTree as ET
from config import config
from logger import logger

def get_wbi_sign(params: dict) -> tuple[str, str]:
    """生成 Wbi 签名"""
    mixinKeyEncTab = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52
    ]
    
    wts = str(int(time.time()))
    params_str = '&'.join([f'{k}={v}' for k, v in sorted(params.items())]) + f'&wts={wts}'
    
    mixin_key = ''.join([chr((i + 256 - mixinKeyEncTab[i]) % 128) for i in range(len(mixinKeyEncTab))])
    str_to_hash = params_str + mixin_key
    w_rid = hashlib.md5(str_to_hash.encode()).hexdigest()
    
    return w_rid, wts

def get_video_parts(bvid: str) -> List[Tuple[int, str, int]]:
    """获取视频分P信息"""
    url = f"https://api.bilibili.com/x/player/pagelist?bvid={bvid}"
    headers = {
        'User-Agent': config.bilibili['user_agent']
    }   
    response = requests.get(url, headers=headers, timeout=10)
    result = response.json()
    if result["code"] != 0:
        raise Exception(f"获取视频分P失败: {result['message']}")
    return [(item["cid"], item["part"], item['duration']) for item in result["data"]]

def send_danmaku(oid: int, message: str, bvid: str, progress: int, csrf: str, sessdata: str) -> tuple[bool, str, dict]:
    """发送弹幕"""
    base_url = "https://api.bilibili.com/x/v2/dm/post"
    
    params = {
        "type": 1,
        "oid": oid,
        "msg": message,
        "bvid": bvid,
        "progress": progress,
        "color": 16777215,
        "mode": 1,
        "rnd": int(time.time() * 1000000),
        "csrf": csrf
    }
    
    w_rid, wts = get_wbi_sign(params)
    url = f"{base_url}?web_location=1315873&w_rid={w_rid}&wts={wts}"
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": f"SESSDATA={sessdata}; bili_jct={csrf}",
        'User-Agent': config.bilibili['user_agent']
    }
    
    try:
        response = requests.post(url, data=params, headers=headers, timeout=10)
        result = response.json()
        success = result["code"] == 0
        message = handle_response_code(result["code"])
        
        # 当遇到登录失效或csrf校验失败时，尝试刷新cookie
        if result["code"] in [-101, -111]:
            logger.warning(f"Cookie失效，尝试刷新: {message}")
            from cookie_refresh import refresh_all_cookies
            
            try:
                new_accounts = refresh_all_cookies()
            except Exception as e:
                logger.error(f"刷新Cookie失败: {e}")
                return False, "Cookie刷新失败", {}

            
            # 如果刷新成功，使用新的cookie重试
            if new_accounts:
                for account in new_accounts:
                    if account['csrf'] == csrf:
                        logger.info("使用新的Cookie重试发送弹幕")
                        return send_danmaku(oid, message, bvid, progress, 
                                         account['csrf'], account['sessdata'])
        
        return success, message, result
    except Exception as e:
        return False, f"请求发生错误: {str(e)}", {}

def handle_response_code(code: int) -> str:
    """处理B站API返回的状态码"""
    code_messages = {
        0: "发送成功",
        -101: "账号未登录",
        -102: "账号被封停",
        -111: "csrf校验失败",
        -400: "请求错误",
        -404: "无此项",
        36700: "系统升级中",
        36701: "弹幕包含被禁止的内容",
        36702: "弹幕长度大于100",
        36703: "发送频率过快",
        36704: "禁止向未审核的视频发送弹幕",
        36705: "您的等级不足，不能发送弹幕",
        36714: "弹幕时间不合法",
    }
    return code_messages.get(code, f"未知错误，错误码：{code}")

def filter_danmaku(danmaku_list: List[Tuple[float, str]], max_count_per_hour: int = 500, time_window: float = 0.5) -> List[Tuple[float, str]]:
    """
    过滤弹幕，确保均匀分布、去重，并且过滤包含禁用关键词的弹幕

    参数:
        danmaku_list: 原始弹幕列表 [(时间戳, 内容),...]
        max_count_per_hour: 每小时最大弹幕数
        time_window: 时间窗口（秒）
    返回:
        过滤后的弹幕列表
    """
    if not danmaku_list:
        return []
    
    # 从配置中获取禁用关键词列表
    banned_keywords = config.danmaku.get("ban_keywords", [])
    
    # 先过滤掉包含禁用关键词的弹幕
    danmaku_list = [
        (timestamp, content) 
        for timestamp, content in danmaku_list 
        if content and not any(keyword in content for keyword in banned_keywords)
    ]

    # 如果全部弹幕均被过滤，则直接返回空列表
    if not danmaku_list:
        return []

    # 按时间排序
    danmaku_list.sort(key=lambda x: x[0])
    
    # 获取视频总时长（小时）
    video_duration = danmaku_list[-1][0] / 3600
    
    # 计算实际每小时最大弹幕数
    max_count = int(max_count_per_hour * video_duration)
    if max_count == 0:
        return []
    
    # 去重
    seen_contents = set()
    unique_danmaku = []
    for timestamp, content in danmaku_list:
        if content not in seen_contents:
            unique_danmaku.append((timestamp, content))
            seen_contents.add(content)
    
    # 如果去重后数量小于限制，直接返回
    if len(unique_danmaku) <= max_count:
        return unique_danmaku
    
    # 计算时间窗口大小，确保弹幕均匀分布
    window_size = (unique_danmaku[-1][0] - unique_danmaku[0][0]) / max_count
    
    # 使用滑动窗口选择弹幕
    filtered_danmaku = []
    current_window_start = unique_danmaku[0][0]
    window_danmaku = []
    
    for timestamp, content in unique_danmaku:
        # 如果当前弹幕时间超出了当前窗口
        while timestamp > current_window_start + window_size:
            # 从当前窗口中选择一条弹幕（如果有的话）
            if window_danmaku:
                # 选择窗口中间位置的弹幕
                mid_idx = len(window_danmaku) // 2
                filtered_danmaku.append(window_danmaku[mid_idx])
            window_danmaku = []
            current_window_start += window_size
        
        window_danmaku.append((timestamp, content))
    
    # 处理最后一个窗口的弹幕
    if window_danmaku:
        mid_idx = len(window_danmaku) // 2
        filtered_danmaku.append(window_danmaku[mid_idx])
    
    return filtered_danmaku

def auto_send_danmaku(xml_path: str, video_cid: int, video_duration: int, bvid: str):
    """自动发送XML文件中的弹幕"""
    
    start_time = time.time()  # 记录开始时间
    
    # 读取XML文件
    tree = ET.parse(xml_path)
    root = tree.getroot()
    danmaku_list = []
    
    # 收集所有弹幕
    for d in root.findall('d'):
        p_attrs = d.get('p').split(',')
        time_stamp = float(p_attrs[0])
        content = d.text
        danmaku_list.append((time_stamp, content))
    
    # 过滤和均匀分布弹幕
    filtered_danmaku = filter_danmaku(
        danmaku_list,
        max_count_per_hour=config.danmaku['max_count_per_hour'],
        time_window=1
    )
    
    logger.info(f"原始弹幕数量: {len(danmaku_list)}, 过滤后数量: {len(filtered_danmaku)}")
    
    # 发送弹幕
    rate_limit_wait = config.danmaku['send_interval']  # 初始等待时间
    accounts = config.bilibili['accounts']
    batch_size = 2  # 每批账号数量
    success_streak = 0  # 连续成功的批次数
    danmaku_count = 0
    
    # 将账号分批
    account_batches = [accounts[i:i+batch_size] for i in range(0, len(accounts), batch_size)]
    current_batch = 0
    
    for i in range(0, len(filtered_danmaku), batch_size):
        batch_danmaku = filtered_danmaku[i:i+batch_size]
        current_accounts = account_batches[current_batch]
        rate_limited = False
        
        # 并行发送当前批次的弹幕
        for j, (timestamp, content) in enumerate(batch_danmaku):
            account_index = j % len(current_accounts)
            current_account = current_accounts[account_index]
            success, message, result = send_danmaku(
                oid=video_cid,
                bvid=bvid,
                message=content,
                progress=max(int(timestamp * 1000), video_duration * 1000),
                csrf=current_account['csrf'],
                sessdata=current_account['sessdata']
            )
            
            logger.info(f"({danmaku_count+j+1}/{len(filtered_danmaku)}) {current_account['uname']:<16}(Lv{current_account['level']}) 发送弹幕: ({time.strftime('%H:%M:%S', time.gmtime(timestamp))}) {content}")
            
            if not success:
                if message in ["账号未登录", "csrf校验失败"]:
                    # 如果是cookie失效，跳过这个账号
                    continue
                    
                if "发送频率过快" in message:
                    rate_limited = True
                    break
                else:
                    logger.warning(f"状态: 失败, 消息: {message}")  
        
        danmaku_count += len(batch_danmaku)
        
        # 处理频率限制情况
        if rate_limited:
            if len(account_batches) == 1:
                # 只有一个批次时，直接增加等待时间
                rate_limit_wait = min(int(rate_limit_wait * 2), 60)  # 最大等待时间60秒
                logger.warning(f"频率限制，等待时间增加到 {rate_limit_wait} 秒")
            else:
                # 多个批次时，先检查成功次数
                if success_streak < 5:
                    logger.warning(f"成功次数过少({success_streak}次)，歇一下 60 秒")
                    time.sleep(60)
                # 切换到下一批账号
                current_batch = (current_batch + 1) % len(account_batches)
                logger.info(f"切换到第 {current_batch + 1} 批账号")
            success_streak = 0  # 重置连续成功计数
        else:
            success_streak += 1
            rate_limit_wait = max(int(rate_limit_wait * 0.8), config.danmaku['send_interval'])
        
        time.sleep(rate_limit_wait)
    
    # 计算并打印总耗时
    total_time = time.time() - start_time
    hours = int(total_time // 3600)
    minutes = int((total_time % 3600) // 60)
    seconds = int(total_time % 60)
    
    logger.info(f"弹幕发送完成，总耗时: {hours:02d}:{minutes:02d}:{seconds:02d}")

def check_up_latest_video(mid: str, title_keyword: str, after_timestamp: int) -> str:
    """
    检查UP主最新视频
    
    参数:
        mid: UP主的mid
        title_keyword: 视频标题关键词
        after_timestamp: 起始时间戳
    
    返回:
        str: 符合条件的视频bvid，如果没找到返回空字符串
    """
    url = f"https://app.bilibili.com/x/v2/space/archive/cursor?vmid={mid}&order=pubdate"

    headers = {
        'User-Agent': config.bilibili['user_agent']
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        result = response.json()
        if result["code"] != 0:
            print(f"请求失败: {result['message']}")
            return ""
        
        # 获取视频列表
        vlist = result["data"]["item"]
        closest_video = None
        min_time_diff = float('inf')
        
        # 遍历视频列表找出时间最接近的视频
        for video in vlist:
            # 只考虑发布时间晚于after_timestamp的视频
            if video["ctime"] <= after_timestamp:
                continue
                
            time_diff = video["ctime"] - after_timestamp
            if time_diff < min_time_diff and title_keyword.lower() in video["title"].lower():
                min_time_diff = time_diff
                closest_video = video
        
        return closest_video["bvid"] if closest_video else ""
        
    except Exception as e:
        print(f"请求发生错误: {str(e)}")
        return ""
