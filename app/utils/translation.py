import hashlib
import random
import requests
import logging
from typing import Tuple, Optional
from datetime import datetime
from flask import current_app
from concurrent.futures import ThreadPoolExecutor
from app.config import Config
from app.utils.epo_api import EPOAPI

class TranslationService:
    """多引擎翻译服务"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.logger = logging.getLogger(__name__)

    def translate_patent_text(
        self,
        text: str,
        patent_number: Optional[str] = None,
        prefer_epo: bool = True
    ) -> Tuple[str, str]:
        """
        专利文本翻译（自动选择最佳来源）
        :param text: 待翻译文本
        :param patent_number: 专利号（用于EPO查询）
        :param prefer_epo: 是否优先使用EPO官方翻译
        :return: (翻译结果, 来源)
        """
        if not text.strip():
            return "", "none"

        # 尝试EPO官方翻译
        if prefer_epo and patent_number:
            try:
                epo_result = self._try_epo_translation(patent_number)
                if epo_result:
                    return epo_result, "epo"
            except Exception as e:
                self.logger.warning(f"EPO翻译失败: {str(e)}")

        # 并行尝试多个机器翻译引擎
        futures = [
            self.executor.submit(self._baidu_translate, text),
            self.executor.submit(self._google_translate, text)
        ]

        # 获取第一个成功的结果
        for future in futures:
            try:
                result = future.result(timeout=5)
                if result:
                    return result, "machine"
            except Exception:
                continue

        return text, "original"

    def _try_epo_translation(self, patent_number: str) -> Optional[str]:
        """尝试从EPO获取官方翻译"""
        epo_data = EPOAPI.search_patent(patent_number)
        
        # 优先返回英文标题和摘要
        if epo_data.get('title_en'):
            result = epo_data['title_en']
            if epo_data.get('abstract_en'):
                result += "\n\n" + epo_data['abstract_en']
            return result
        
        return None

    def _baidu_translate(self, text: str) -> Optional[str]:
        """百度翻译API"""
        if not all([Config.BAIDU_TRANSLATE_APP_ID, Config.BAIDU_TRANSLATE_SECRET_KEY]):
            return None

        salt = str(random.randint(32768, 65536))
        sign_str = f"{Config.BAIDU_TRANSLATE_APP_ID}{text}{salt}{Config.BAIDU_TRANSLATE_SECRET_KEY}"
        sign = hashlib.md5(sign_str.encode()).hexdigest()

        params = {
            'q': text,
            'from': 'zh',
            'to': 'en',
            'appid': Config.BAIDU_TRANSLATE_APP_ID,
            'salt': salt,
            'sign': sign
        }

        try:
            response = requests.post(
                "https://api.fanyi.baidu.com/api/trans/vip/translate",
                params=params,
                timeout=5
            )
            data = response.json()
            
            if 'trans_result' in data:
                return '\n'.join(item['dst'] for item in data['trans_result'])
        except Exception as e:
            self.logger.error(f"百度翻译失败: {str(e)}")
            return None

    def _google_translate(self, text: str) -> Optional[str]:
        """Google翻译（模拟API）"""
        # 实际实现需要替换为真实API调用
        return None

    def batch_translate(
        self,
        texts: list,
        patent_numbers: Optional[list] = None
    ) -> list:
        """
        批量翻译专利文本
        :param texts: 待翻译文本列表
        :param patent_numbers: 对应的专利号列表
        :return: 翻译结果列表 [(text, source), ...]
        """
        if patent_numbers and len(texts) != len(patent_numbers):
            raise ValueError("文本与专利号数量不匹配")

        results = []
        for i, text in enumerate(texts):
            pn = patent_numbers[i] if patent_numbers else None
            results.append(self.translate_patent_text(text, pn))
        
        return results

    def get_translation_quality(self, source: str) -> float:
        """
        获取翻译质量评分（0-1）
        :param source: 翻译来源 (epo/machine/original)
        """
        return {
            'epo': 0.95,
            'machine': 0.75,
            'original': 0.0
        }.get(source, 0.5)

# 单例服务实例
translation_service = TranslationService()

# 兼容旧API
def translate_patent_text(text: str, patent_number: Optional[str] = None) -> Tuple[str, str]:
    """兼容旧版翻译函数"""
    return translation_service.translate_patent_text(text, patent_number)

def baidu_translate(text: str) -> str:
    """兼容旧版百度翻译"""
    result, _ = translation_service.translate_patent_text(text, prefer_epo=False)
    return result