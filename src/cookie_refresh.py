import time
import requests
import re
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
import binascii
from logger import logger
from config import config


class CookieRefresher:
    def __init__(self):
        self.public_key = RSA.importKey('''\
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLgd2OAkcGVtoE3ThUREbio0Eg
Uc/prcajMKXvkCKFCWhJYJcLkcM2DKKcSeFpD/j6Boy538YXnR6VhcuUJOhH2x71
nzPjfdTcqMz7djHum0qSZA0AyCBDABUqCrfNgCiJ00Ra7GmRj+YCK1NJEuewlb40
JNrRuoEUXpabUzGB8QIDAQAB
-----END PUBLIC KEY-----''')

    def get_correspond_path(self, ts: int) -> str:
        """生成CorrespondPath"""
        ts -= 20 * 1000
        cipher = PKCS1_OAEP.new(self.public_key, SHA256)
        encrypted = cipher.encrypt(f'refresh_{ts}'.encode())
        return binascii.b2a_hex(encrypted).decode()

    def check_need_refresh(self, account: dict) -> bool:
        """检查是否需要刷新Cookie"""
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"
        headers = {
            'Cookie': f"SESSDATA={account['sessdata']}; bili_jct={account['csrf']}",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        }

        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            if data['code'] != 0:
                return True
            return data.get('data', {}).get('refresh', False)
        except Exception as e:
            logger.error(f"检查Cookie刷新状态失败: {str(e)}")
            return False

    def get_refresh_csrf(self, account: dict) -> str:
        """获取refresh_csrf"""
        ts = round(time.time() * 1000)
        correspond_path = self.get_correspond_path(ts)
        url = f"https://www.bilibili.com/correspond/1/{correspond_path}"
        headers = {'Cookie': f"SESSDATA={account['sessdata']}",
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', }
        try:
            response = requests.get(url, headers=headers)
            # 使用正则表达式从HTML中提取refresh_csrf
            match = re.search(r'<div id="1-name">([^<]+)</div>', response.text)
            if match:
                return match.group(1)
        except Exception as e:
            logger.error(f"获取refresh_csrf失败: {str(e)}")
        return ""

    def refresh_cookie(self, account: dict) -> dict:
        """刷新Cookie"""
        if not self.check_need_refresh(account):
            return account

        logger.info(f"账号 {account['csrf'][:8]} 的Cookie需要刷新")
        refresh_csrf = self.get_refresh_csrf(account)
        if not refresh_csrf:
            logger.error(f"获取refresh_csrf失败，无法刷新Cookie")
            return account

        logger.info(f"获取到refresh_csrf: {refresh_csrf}")

        url = "https://passport.bilibili.com/x/passport-login/web/cookie/refresh"
        data = {
            'csrf': account['csrf'],
            'refresh_csrf': refresh_csrf,
            'source': 'main_web',
            'refresh_token': account.get('refresh_token', '')
        }
        headers = {'Cookie': f"SESSDATA={account['sessdata']}; bili_jct={account['csrf']}",
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', }

        try:
            response = requests.post(url, data=data, headers=headers)
            result = response.json()

            if result['code'] == 0:
                # 从响应头中获取新的Cookie
                cookies = response.cookies
                new_account = {
                    'csrf': cookies.get('bili_jct', account['csrf']),
                    'sessdata': cookies.get('SESSDATA', account['sessdata']),
                    'refresh_token': result['data']['refresh_token']
                }

                # 确认更新
                self.confirm_refresh(new_account, account['refresh_token'])
                logger.info(f"Cookie刷新成功")
                return new_account

        except Exception as e:
            logger.error(f"刷新Cookie失败: {str(e)}")

        return account

    def confirm_refresh(self, new_account: dict, old_refresh_token: str):
        """确认更新"""
        url = "https://passport.bilibili.com/x/passport-login/web/confirm/refresh"
        data = {
            'csrf': new_account['csrf'],
            'refresh_token': old_refresh_token
        }
        headers = {'Cookie': f"SESSDATA={new_account['sessdata']}; bili_jct={new_account['csrf']}",
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'}

        try:
            response = requests.post(url, data=data, headers=headers)
            if response.json()['code'] == 0:
                logger.info("Cookie更新确认成功")
        except Exception as e:
            logger.error(f"确认更新失败: {str(e)}")


def refresh_all_cookies():
    """刷新所有账号的Cookie"""
    refresher = CookieRefresher()
    new_accounts = []
    config_changed = False

    for account in config.bilibili['accounts']:
        logger.info(f"正在检查账号 {account['csrf'][:8]}... 的Cookie状态")
        new_account = refresher.refresh_cookie(account)
        new_accounts.append(new_account)

        # 检查是否有更新
        if (new_account['csrf'] != account['csrf'] or
                new_account['sessdata'] != account['sessdata'] or
                new_account['refresh_token'] != account['refresh_token']):
            config_changed = True

    # 如果有更新，保存到配置文件
    if config_changed:
        config.bilibili['accounts'] = new_accounts
        config.save()
        logger.info("已更新配置文件中的Cookie信息")

    return new_accounts
