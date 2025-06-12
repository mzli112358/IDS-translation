import requests
import time
from requests.exceptions import RequestException
from datetime import datetime, timedelta
from flask import current_app
from app.config import Config

class EPOAuth:
    """EPO OPS API 认证管理器"""
    
    _token = None
    _token_expiry = None
    _last_refresh = None
    _retry_count = 0
    MAX_RETRIES = 3

    @classmethod
    def get_access_token(cls, force_refresh=False):
        """
        获取有效的Access Token
        :param force_refresh: 强制刷新Token
        :return: str 有效的access_token
        :raises: Exception 当认证失败时抛出
        """
        # 如果存在有效Token且不强制刷新
        if not force_refresh and cls._is_token_valid():
            return cls._token

        try:
            # 重试机制
            for attempt in range(cls.MAX_RETRIES):
                try:
                    # 请求Token
                    auth = (Config.EPO_OPS_CONSUMER_KEY, Config.EPO_OPS_SECRET_KEY)
                    response = requests.post(
                        Config.EPO_OPS_TOKEN_URL,
                        auth=auth,
                        headers={
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'User-Agent': 'IDS-Patent-Translator/1.0'
                        },
                        data={'grant_type': 'client_credentials'},
                        timeout=10  # 10秒超时
                    )
                    response.raise_for_status()

                    # 处理响应
                    data = response.json()
                    cls._update_token_data(data)
                    cls._retry_count = 0  # 重置重试计数器
                    return cls._token

                except RequestException as e:
                    cls._retry_count += 1
                    if attempt == cls.MAX_RETRIES - 1:
                        raise
                    time.sleep(2 ** cls._retry_count)  # 指数退避

        except Exception as e:
            current_app.logger.error(
                f"EPO认证失败 (尝试 {cls._retry_count+1}/{cls.MAX_RETRIES}): {str(e)}"
            )
            cls.clear_token()
            raise Exception(
                f"无法获取EPO访问令牌: {str(e)}. "
                f"请检查API密钥配置或网络连接。"
            )

    @classmethod
    def _is_token_valid(cls):
        """检查当前Token是否有效"""
        if not cls._token or not cls._token_expiry:
            return False
        
        # 添加60秒缓冲期
        return datetime.utcnow() < cls._token_expiry - timedelta(seconds=60)

    @classmethod
    def _update_token_data(cls, token_data):
        """更新Token数据并计算过期时间"""
        cls._token = token_data['access_token']
        
        # 确保expires_in是有效的整数
        expires_in = int(token_data.get('expires_in', 1200))  # 默认20分钟
        cls._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        cls._last_refresh = datetime.utcnow()

    @classmethod
    def get_token_info(cls):
        """获取当前Token状态信息"""
        return {
            'has_token': bool(cls._token),
            'expires_at': cls._token_expiry.isoformat() if cls._token_expiry else None,
            'last_refresh': cls._last_refresh.isoformat() if cls._last_refresh else None,
            'will_expire_in': (
                (cls._token_expiry - datetime.utcnow()).total_seconds() 
                if cls._is_token_valid() else 0
            ),
            'retry_count': cls._retry_count
        }

    @classmethod
    def clear_token(cls):
        """强制清除当前Token状态"""
        cls._token = None
        cls._token_expiry = None
        cls._last_refresh = None

    @classmethod
    def auth_header(cls):
        """
        生成认证Header字典
        :return: dict {'Authorization': 'Bearer <token>'}
        :raises: Exception 当Token无效时抛出
        """
        token = cls.get_access_token()
        return {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }

# 测试用代码（开发时使用）
if __name__ == '__main__':
    from app import create_app
    app = create_app(Config)
    with app.app_context():
        try:
            token = EPOAuth.get_access_token()
            print("Token获取成功:", token)
            print("Token信息:", EPOAuth.get_token_info())
        except Exception as e:
            print("Token获取失败:", str(e))