import requests
import qrcode
import time
from config import config
from logger import logger


def get_user_info(sessdata: str) -> tuple[bool, dict]:
    """获取用户信息"""
    url = "https://api.bilibili.com/x/web-interface/nav"
    headers = {
        'User-Agent': config.bilibili['user_agent'],
        'Cookie': f'SESSDATA={sessdata}'
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()

        if data['code'] != 0:
            return False, {}

        user_data = data['data']
        return True, {
            'mid': user_data['mid'],
            'uname': user_data['uname'],
            'level': user_data['level_info']['current_level']
        }
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        return False, {}


class BilibiliLogin:
    def __init__(self):
        self.session = requests.Session()

    def generate_qrcode(self) -> tuple[str, str]:
        """生成登录二维码"""
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"

        try:
            headers = {'User-Agent': config.bilibili['user_agent']}
            response = self.session.get(url, headers=headers)
            data = response.json()

            if data['code'] != 0:
                raise Exception(f"获取二维码失败: {data['message']}")

            qr_url = data['data']['url']
            qrcode_key = data['data']['qrcode_key']

            # 在控制台打印二维码
            qr = qrcode.QRCode(border=1)
            qr.add_data(qr_url)
            qr.make(fit=True)
            qr.print_ascii(invert=True)  # 使用ASCII字符打印

            logger.info("请使用手机扫描上方二维码")
            return qrcode_key, qr_url

        except Exception as e:
            logger.error(f"生成二维码失败: {str(e)}")
            raise

    def poll_login_status(self, qrcode_key: str) -> tuple[int, dict]:
        """轮询登录状态"""
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
        params = {'qrcode_key': qrcode_key}

        try:
            headers = {'User-Agent': config.bilibili['user_agent']}
            response = self.session.get(url, params=params, headers=headers)
            data = response.json()

            cookies = {}
            if data['code'] == 0:
                # 获取cookies
                if response.cookies:
                    for cookie in response.cookies:
                        cookies[cookie.name] = cookie.value
                # 获取refresh_token
                if 'data' in data and 'refresh_token' in data['data']:
                    cookies['refresh_token'] = data['data']['refresh_token']

            return data['data']['code'], cookies

        except Exception as e:
            logger.error(f"检查登录状态失败: {str(e)}")
            return -1, {}

    def wait_for_scan(self, qrcode_key: str, timeout: int = 180) -> dict:
        """等待扫码结果"""
        start_time = time.time()
        last_status = None

        while time.time() - start_time < timeout:
            status, cookies = self.poll_login_status(qrcode_key)

            if status != last_status:
                if status == 0:
                    logger.info("扫码成功！登录成功")
                    return cookies
                elif status == 86090:
                    logger.info("扫码成功！等待确认...")
                elif status == 86038:
                    logger.warning("二维码已失效，请重新获取")
                    return {}

                last_status = status

            time.sleep(1)

        logger.warning("登录超时")
        return {}


def add_account():
    """添加新账号"""
    login = BilibiliLogin()

    try:
        # 生成二维码
        qrcode_key, _ = login.generate_qrcode()

        # 等待扫码
        cookies = login.wait_for_scan(qrcode_key)

        if not cookies:
            logger.error("登录失败")
            return

        # 获取必要的cookie
        csrf = cookies.get('bili_jct', '')
        sessdata = cookies.get('SESSDATA', '')

        if not csrf or not sessdata:
            logger.error("获取Cookie失败")
            return

        # 在获取到cookies后，获取用户信息
        success, user_info = get_user_info(sessdata)
        if not success:
            logger.error("获取用户信息失败")
            return

        # 更新配置文件
        new_account = {
            "csrf": csrf,
            "sessdata": sessdata,
            "refresh_token": cookies.get('refresh_token', ''),
            "mid": user_info['mid'],
            "uname": user_info['uname'],
            "level": user_info['level'],
            "expired": False
        }

        # 确保accounts列表存在
        if 'accounts' not in config.bilibili:
            config.bilibili['accounts'] = []
        elif config.bilibili['accounts'] is None:
            config.bilibili['accounts'] = []

        # 检查是否已存在相同账号
        accounts = config.bilibili['accounts']
        for i, account in enumerate(accounts):
            if account['mid'] == user_info['mid']:
                accounts[i] = new_account
                logger.info(f"更新已存在的账号: {user_info['uname']}")
                break
        else:
            accounts.append(new_account)
            logger.info(f"添加新账号: {user_info['uname']}")

        config.save()
        logger.info("账号信息已存到配置文件")

    except Exception as e:
        import traceback
        logger.error(f"详细错误信息:\n{traceback.format_exc()}")
        logger.error(f"添加账号失败: {str(e)}")


if __name__ == "__main__":
    add_account()
