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

def send_danmaku(oid: int, message: str, bvid: str, progress: int, color: int, csrf: str, sessdata: str) -> tuple[bool, str, dict]:
    """发送弹幕"""
    base_url = "https://api.bilibili.com/x/v2/dm/post"
    
    params = {
        "type": 1,
        "oid": oid,
        "msg": message,
        "bvid": bvid,
        "progress": progress,
        "color": color,
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
                        return send_danmaku(oid, message, bvid, progress, color,
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

def filter_danmaku(
    danmaku_list: List[Tuple[float, str, str, str]],
    max_count_per_hour: int = 500,
    max_repeat_count: int = 1,
) -> List[Tuple[float, str]]:
    """根据原始内容过滤弹幕并均匀分布普通弹幕

    ``danmaku_list`` 每项为 ``(timestamp, message, original, type)``，其中
    ``type`` 为 ``"d"`` 或 ``"gift"``。礼物弹幕不会被计入频率限制或重复
    限制，但仍会按时间排序返回。
    """
    if not danmaku_list:
        return []
    
    # 从配置中获取禁用关键词列表
    banned_keywords = config.danmaku.get("ban_keywords", [])

    # 先过滤掉包含禁用关键词的弹幕（礼物弹幕不过滤）
    danmaku_list = [
        item
        for item in danmaku_list
        if (
            item[3] == "gift"
            or (item[2] and not any(k in item[2] for k in banned_keywords))
        )
    ]

    # 如果全部弹幕均被过滤，则直接返回空列表
    if not danmaku_list:
        return []

    # 按时间排序
    danmaku_list.sort(key=lambda x: x[0])
    
    # 去重并检查重复次数（礼物弹幕不去重）
    seen_contents: dict[str, int] = {}
    unique_danmaku: List[Tuple[float, str, str, str]] = []
    for item in danmaku_list:
        ts, msg, orig, typ = item
        if typ == "gift":
            unique_danmaku.append(item)
            continue
        seen_contents[orig] = seen_contents.get(orig, 0) + 1
        if seen_contents[orig] <= max_repeat_count:
            unique_danmaku.append(item)

    # 筛选出普通弹幕用于计算频率
    normal_danmaku = [d for d in unique_danmaku if d[3] != "gift"]
    if not normal_danmaku:
        return [(t, m) for t, m, _, _ in unique_danmaku]

    # 获取视频总时长（小时）
    video_duration = danmaku_list[-1][0] / 3600
    
    # 计算实际每小时最大弹幕数
    max_count = int(max_count_per_hour * video_duration)
    if max_count == 0:
        return []
    
    # 如果去重后数量小于限制，直接返回
    if len(normal_danmaku) <= max_count:
        final_normal = normal_danmaku
    else:
        # 计算时间窗口大小，确保弹幕均匀分布
        window_size = (normal_danmaku[-1][0] - normal_danmaku[0][0]) / max_count

        # 使用滑动窗口选择弹幕
        final_normal: List[Tuple[float, str, str, str]] = []
        current_window_start = normal_danmaku[0][0]
        window_danmaku: List[Tuple[float, str, str, str]] = []

        for i, item in enumerate(normal_danmaku):
            ts = item[0]
            if len(final_normal) + (len(normal_danmaku) - i) <= max_count:
                if window_danmaku:
                    mid_idx = len(window_danmaku) // 2
                    final_normal.append(window_danmaku[mid_idx])
                    window_danmaku = []
                final_normal.extend(normal_danmaku[i:])
                break

            while ts > current_window_start + window_size:
                if window_danmaku:
                    mid_idx = len(window_danmaku) // 2
                    final_normal.append(window_danmaku[mid_idx])
                window_danmaku = []
                current_window_start += window_size

            window_danmaku.append(item)

        if window_danmaku:
            mid_idx = len(window_danmaku) // 2
            final_normal.append(window_danmaku[mid_idx])

    # 礼物弹幕保持原顺序加入
    gifts = [d for d in unique_danmaku if d[3] == "gift"]
    result = final_normal + gifts
    result.sort(key=lambda x: x[0])

    return [(ts, msg, tpe) for ts, msg, _, tpe in result]


def _parse_gift(elem: ET.Element, base_timestamp: float | None) -> tuple[float, str, str, str] | None:
    """将礼物弹幕元素转换为时间戳和消息文本

    返回 ``(time, message, original_content, 'gift')``，若 ``base_timestamp`` 未确定则返回 ``None``。
    """
    since_start = elem.get('since_start')
    if since_start is not None:
        time_stamp = float(since_start)
    elif base_timestamp is not None:
        abs_time = float(elem.get('timestamp', '0'))
        time_stamp = abs_time - base_timestamp
    else:
        return None
    uname = elem.get('username', '')
    uid = elem.get('uid', '')
    giftname = elem.get('giftname', '')
    num = elem.get('num', '')
    message = f"{uname}({uid}) donate {giftname} x{num}"
    if giftname.startswith("点亮"):
        message = f"{uname}({uid}) {giftname}"
    original = f"{giftname} x{num}"
    return time_stamp, message, original, "gift"


def _flush_gifts(
    pending_gifts: List[ET.Element],
    base_timestamp: float,
    danmaku_list: List[Tuple[float, str, str, str]],
) -> None:
    """将缓存的礼物弹幕转换为普通弹幕格式并加入列表"""
    for g in pending_gifts:
        parsed = _parse_gift(g, base_timestamp)
        if parsed is not None:
            danmaku_list.append(parsed)
    pending_gifts.clear()


def _parse_gift(elem: ET.Element, base_timestamp: float | None) -> tuple[float, str, str, str] | None:
    """将礼物弹幕元素转换为时间戳和消息文本"""
    since_start = elem.get('since_start')
    if since_start is not None:
        time_stamp = float(since_start)
    elif base_timestamp is not None:
        abs_time = float(elem.get('timestamp', '0'))
        time_stamp = abs_time - base_timestamp
    else:
        return None
    uname = elem.get('username', '')
    uid = elem.get('uid', '')
    giftname = elem.get('giftname', '')
    num = elem.get('num', '')
    original = f"{giftname} x{num}"
    message = f"{uname}({uid}) donate {giftname} x{num}"
    if giftname.startswith("点亮"):
        message = f"{uname}({uid}) {giftname}"
    return time_stamp, message, original, "gift"


def _flush_gifts(pending_gifts: List[ET.Element], base_timestamp: float, danmaku_list: List[Tuple[float, str]]):
    """将缓存的礼物弹幕转换为普通弹幕格式并加入列表"""
    for g in pending_gifts:
        parsed = _parse_gift(g, base_timestamp)
        if parsed is not None:
            danmaku_list.append(parsed)
    pending_gifts.clear()


def auto_send_danmaku(xml_path: str, video_cid: int, video_duration: int, bvid: str):
    """根据XML文件内容自动发送弹幕

    XML中 ``<d>`` 标签表示普通弹幕，``<s type="gift">`` 表示礼物弹幕。
    礼物弹幕未来可能包含 ``since_start``，表示距离视频开始的时间；
    若没有该字段，则通过 ``timestamp`` 与普通弹幕推算基准时间。
    普通弹幕会封装为 ``[用户名]([用户id])：[内容]``，礼物弹幕会封装为
    ``[用户名]([用户id]) donate [礼物名称] x[礼物数量]``。
    
    """
    
    start_time = time.time()  # 记录开始时间
    
    # 读取XML文件
    tree = ET.parse(xml_path)
    root = tree.getroot()
    danmaku_list: List[Tuple[float, str, str, str]] = []
    base_timestamp = None  # 视频开始的 Unix 时间戳
    pending_gifts: List[ET.Element] = []

    # 收集所有弹幕
    for elem in root:
        if elem.tag == 'd':
            # 普通弹幕
            p_attr = elem.get('p')
            rel_time = float(p_attr.split(',')[0]) if p_attr else 0.0
            abs_time = float(elem.get('timestamp', '0'))

            if base_timestamp is None:
                base_timestamp = abs_time - rel_time
                _flush_gifts(pending_gifts, base_timestamp, danmaku_list)

            time_stamp = rel_time if p_attr else abs_time - base_timestamp

            content = elem.text or ""
            uname = elem.get('user', '')
            uid = elem.get('uid', '')
            if uname == '' or uid == '':
                message = content
            else:
                message = f"{uname}({uid})：{content}"
            danmaku_list.append((time_stamp, message, content, "d"))


        elif elem.tag == 's' and elem.get('type') == 'gift':
            parsed = _parse_gift(elem, base_timestamp)
            if parsed is None:
                pending_gifts.append(elem)
            else:
                danmaku_list.append(parsed)

    # 若遍历结束后仍未确定基准时间，使用最早礼物弹幕时间作为基准
    if pending_gifts:
        if base_timestamp is None:
            base_timestamp = float(pending_gifts[0].get('timestamp', '0'))
        _flush_gifts(pending_gifts, base_timestamp, danmaku_list)
    
    # 过滤和均匀分布弹幕
    filtered_danmaku = filter_danmaku(
        danmaku_list,
        max_count_per_hour=config.danmaku['max_count_per_hour'],
        max_repeat_count=config.danmaku['max_repeat_count']
    )
    
    logger.info(f"原始弹幕数量: {len(danmaku_list)}, 过滤后数量: {len(filtered_danmaku)}")
    
    # 发送弹幕
    rate_limit_wait = config.danmaku['send_interval']  # 初始等待时间
    accounts = config.bilibili['accounts']
    batch_size = config.bilibili['batch_size']  # 每批账号数量
    success_streak = 0  # 连续成功的批次数
    danmaku_count = 0
    
    # 将账号分批
    account_batches = [accounts[i:i+batch_size] for i in range(0, len(accounts), batch_size)]
    current_batch = 0
    
    for i in range(0, len(filtered_danmaku), batch_size):
        batch_danmaku = filtered_danmaku[i:i+batch_size]
        current_accounts = account_batches[current_batch]
        rate_limited = False
        
        # 计算批量账号里面的名字最长的名字个数，名字里面的中文算两个长度
        max_name_length = max(len(account['uname']) + sum(1 for c in account['uname'] if ord(c) > 127) for account in current_accounts)

        # 并行发送当前批次的弹幕
        for j, (timestamp, content, tpe) in enumerate(batch_danmaku):
            progress = max(
                min(int(timestamp * 1000) - 3000, video_duration * 1000),
                0
            )
            account_index = j % len(current_accounts)
            current_account = current_accounts[account_index]
            color = 16776960 if tpe == 'gift' else 16777215
            success, message, result = send_danmaku(
                oid=video_cid,
                bvid=bvid,
                message=content,
                progress=progress,
                color=color,
                csrf=current_account['csrf'],
                sessdata=current_account['sessdata']
            )
            

            # Adjust padding for names with mixed characters (including Chinese)
            adjusted_name = current_account['uname']
            padding_length = max_name_length - len(adjusted_name) - sum(1 for c in adjusted_name if ord(c) > 127)
            logger.info(f"({danmaku_count+j+1}/{len(filtered_danmaku)}) {adjusted_name}{' ' * (padding_length + 5)}(Lv{current_account['level']}) 发送弹幕: ({time.strftime('%H:%M:%S', time.gmtime(progress / 1000))}) {content}")
            
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
