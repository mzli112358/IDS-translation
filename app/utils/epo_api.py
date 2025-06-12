import requests
import json
from datetime import datetime
from flask import current_app
from requests.exceptions import RequestException
from app.utils.epo_auth import EPOAuth
from app.config import Config
from app.utils.validators import validate_patent_number

class EPOAPI:
    """EPO OPS API 服务封装"""
    
    @classmethod
    def search_patent(cls, patent_number, doc_type='biblio'):
        """
        查询专利数据（自动处理认证和重试）
        :param patent_number: 标准化的专利号 (如 EP1000000)
        :param doc_type: 查询类型 (biblio/abstract/claims/description)
        :return: dict 标准化的专利数据
        :raises: Exception 当查询失败时抛出
        """
        # 验证专利号格式
        is_valid, normalized_num = validate_patent_number(patent_number)
        if not is_valid:
            raise ValueError(f"无效的专利号格式: {patent_number}")

        try:
            # 获取API数据
            data = cls._fetch_epo_data(normalized_num, doc_type)
            
            # 标准化处理
            return cls._standardize_data(data, doc_type)
            
        except Exception as e:
            current_app.logger.error(
                f"EPO查询失败 [{normalized_num}]: {str(e)}",
                exc_info=True
            )
            raise

    @classmethod
    def _fetch_epo_data(cls, patent_number, doc_type):
        """实际执行EPO API请求"""
        max_retries = 2
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                url = f"{Config.EPO_OPS_API_URL}published-data/publication/epodoc/{patent_number}/{doc_type}"
                response = requests.get(
                    url,
                    headers=EPOAuth.auth_header(),
                    timeout=15,
                    params={'format': 'json'}
                )
                
                # 处理401过期情况
                if response.status_code == 401 and attempt < max_retries:
                    EPOAuth.clear_token()
                    continue
                    
                response.raise_for_status()
                return response.json()
                
            except RequestException as e:
                last_exception = e
                if attempt == max_retries:
                    raise Exception(
                        f"EPO API请求失败: {str(e)} "
                        f"(尝试 {attempt + 1}/{max_retries + 1})"
                    )

    @classmethod
    def _standardize_data(cls, raw_data, doc_type):
        """标准化EPO返回数据"""
        if doc_type == 'biblio':
            return {
                'patent_number': raw_data.get('publication', {}).get('document-id', {}).get('doc-number'),
                'title': cls._get_text(raw_data.get('bibliographic-data', {}).get('invention-title')),
                'application_date': cls._parse_date(raw_data.get('bibliographic-data', {}).get('application-reference')),
                'publication_date': cls._parse_date(raw_data.get('publication', {}).get('document-id')),
                'applicants': cls._extract_parties(raw_data.get('bibliographic-data', {}).get('parties')),
                'inventors': cls._extract_inventors(raw_data.get('bibliographic-data', {}).get('parties')),
                'ipc_classes': cls._extract_ipc(raw_data.get('bibliographic-data', {}).get('classifications-ipcr')),
                'source': 'epo',
                'retrieved_at': datetime.utcnow().isoformat()
            }
        else:
            return {
                'content': cls._get_text(raw_data),
                'source': 'epo',
                'doc_type': doc_type
            }

    @staticmethod
    def _get_text(text_obj):
        """提取多语言文本（优先返回英文）"""
        if isinstance(text_obj, str):
            return text_obj
        elif isinstance(text_obj, dict):
            return text_obj.get('en', list(text_obj.values())[0])
        elif isinstance(text_obj, list):
            return text_obj[0] if text_obj else None
        return None

    @staticmethod
    def _parse_date(date_obj):
        """解析EPO日期格式"""
        if isinstance(date_obj, dict):
            date_str = date_obj.get('date')
        elif isinstance(date_obj, str):
            date_str = date_obj
        else:
            return None
            
        try:
            return datetime.strptime(date_str, '%Y%m%d').date().isoformat()
        except:
            return None

    @staticmethod
    def _extract_parties(parties_data):
        """提取申请人信息"""
        if not parties_data:
            return []
            
        applicants = parties_data.get('applicants', {}).get('applicant', [])
        if isinstance(applicants, dict):
            applicants = [applicants]
            
        return [app.get('name', {}).get('name') for app in applicants if app]

    @staticmethod
    def _extract_inventors(inventors_data):
        """提取发明人信息"""
        if not inventors_data:
            return []
            
        inventors = inventors_data.get('inventors', {}).get('inventor', [])
        if isinstance(inventors, dict):
            inventors = [inventors]
            
        return [inv.get('name', {}).get('name') for inv in inventors if inv]

    @staticmethod
    def _extract_ipc(ipc_data):
        """提取IPC分类号"""
        if not ipc_data:
            return []
            
        classifications = ipc_data.get('classification-ipcr', [])
        if isinstance(classifications, dict):
            classifications = [classifications]
            
        return [cls.get('text') for cls in classifications if cls]

# 保持旧函数兼容性
def search_patent(patent_number):
    """兼容旧代码的查询函数"""
    return EPOAPI.search_patent(patent_number)

def search_epo_patent(patent_number):
    """兼容旧代码的别名"""
    return EPOAPI.search_patent(patent_number)