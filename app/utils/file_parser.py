import os
import re
import PyPDF2
import pdfplumber
from datetime import datetime
from typing import Dict, Optional, Tuple
from flask import current_app
from app.utils.validators import validate_patent_number

class PDFParser:
    """专利PDF文档解析器"""
    
    @staticmethod
    def parse_pdf(filepath: str) -> Dict[str, str]:
        """
        解析专利PDF文件，提取结构化信息
        :param filepath: PDF文件路径
        :return: 标准化专利信息字典
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")

        try:
            # 先用pdfplumber提取更精确的文本
            with pdfplumber.open(filepath) as pdf:
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                
                # 备用提取方式（PyPDF2）
                if not text or len(text) < 100:
                    text = PDFParser._extract_with_pypdf2(filepath)

            # 标准化文本处理
            text = PDFParser._preprocess_text(text)
            
            # 提取各字段
            return {
                'patent_number': PDFParser._extract_patent_number(text),
                'title': PDFParser._extract_title(text),
                'applicants': PDFParser._extract_applicants(text),
                'inventors': PDFParser._extract_inventors(text),
                'application_date': PDFParser._extract_date(text, 'application'),
                'publication_date': PDFParser._extract_date(text, 'publication'),
                'ipc_class': PDFParser._extract_ipc(text),
                'abstract': PDFParser._extract_abstract(text),
                'source': 'pdf_parse'
            }
            
        except Exception as e:
            current_app.logger.error(f"解析PDF失败: {filepath}, 错误: {str(e)}")
            raise Exception(f"PDF解析失败: {str(e)}")

    @staticmethod
    def _extract_with_pypdf2(filepath: str) -> str:
        """备用文本提取方法"""
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return reader.pages[0].extract_text() or ""

    @staticmethod
    def _preprocess_text(text: str) -> str:
        """文本预处理"""
        # 统一换行符
        text = text.replace('\r\n', '\n')
        # 合并被错误分割的单词
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
        # 去除多余空格
        return re.sub(r'[ \t]{2,}', ' ', text)

    @staticmethod
    def _extract_patent_number(text: str) -> Optional[str]:
        """提取专利号（自动验证格式）"""
        patterns = [
            # 中国专利
            r'(?:专利号|公开号|申请号)[：:\s]*([A-Z]{0,2}\d{6,}[A-Z]?\d?)',
            # 美国专利
            r'(?:Patent|Appl)[\w\s]*No[\.:\s]*([A-Z]{0,2}\d+[,/\d]*)',
            # 欧洲/PCT
            r'(EP|WO|PCT)\s*([A-Z]{0,2}\d+)',
            # 通用格式
            r'\b([A-Z]{2,3}\d{4,}[A-Z]?\d?)\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # 合并捕获组
                number = ''.join(g for g in match.groups() if g)
                is_valid, normalized = validate_patent_number(number)
                if is_valid:
                    return normalized
        return None

    @staticmethod
    def _extract_title(text: str) -> Optional[str]:
        """提取专利标题"""
        patterns = [
            r'名称[：:\s]*(.+?)\n',
            r'Title[：:\s]*(.+?)\n',
            r'(?:发明名称|专利名称)[：:\s]*(.+?)\n'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def _extract_applicants(text: str) -> list:
        """提取申请人列表"""
        patterns = [
            r'申请人[：:\s]*(.+?)\n',
            r'Applicant$s$[：:\s]*(.+?)\n',
            r'Assignees?[：:\s]*(.+?)\n'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                # 分割多个申请人
                applicants = re.split(r'[；;,]', match.group(1))
                return [a.strip() for a in applicants if a.strip()]
        return []

    @staticmethod
    def _extract_inventors(text: str) -> list:
        """提取发明人列表"""
        patterns = [
            r'发明人[：:\s]*(.+?)\n',
            r'Inventor$s$[：:\s]*(.+?)\n'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                # 分割多个发明人
                inventors = re.split(r'[；;,]', match.group(1))
                return [i.strip() for i in inventors if i.strip()]
        return []

    @staticmethod
    def _extract_date(text: str, date_type: str) -> Optional[str]:
        """提取日期并标准化"""
        patterns = {
            'application': [
                r'申请日[：:\s]*(\d{4}[年\-\.]\d{1,2}[月\-\.]\d{1,2})',
                r'Filed[:\s]*(\w+\s\d{1,2},\s\d{4})'
            ],
            'publication': [
                r'公开日[：:\s]*(\d{4}[年\-\.]\d{1,2}[月\-\.]\d{1,2})',
                r'Published[:\s]*(\w+\s\d{1,2},\s\d{4})'
            ]
        }
        
        for pattern in patterns.get(date_type, []):
            match = re.search(pattern, text)
            if match:
                try:
                    date_str = match.group(1)
                    # 中文日期处理
                    if '年' in date_str:
                        date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                        return datetime.strptime(date_str, '%Y-%m-%d').date().isoformat()
                    # 英文日期处理
                    elif re.search(r'[a-zA-Z]', date_str):
                        return datetime.strptime(date_str, '%B %d, %Y').date().isoformat()
                except:
                    continue
        return None

    @staticmethod
    def _extract_ipc(text: str) -> Optional[str]:
        """提取IPC分类号"""
        match = re.search(r'IPC分类号[：:\s]*(.+?)\n', text) or \
                re.search(r'Int\. Cl\.\s*([A-Z]\d{2}[A-Z]\s*\d+/\d+)', text)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_abstract(text: str) -> Optional[str]:
        """提取摘要（简单实现）"""
        start_markers = ['摘要', 'Abstract']
        end_markers = ['权利要求', 'Claims', '技术领域']
        
        for marker in start_markers:
            if marker in text:
                start = text.index(marker) + len(marker)
                end = len(text)
                
                for end_marker in end_markers:
                    if end_marker in text[start:]:
                        end = text.index(end_marker, start)
                        break
                
                abstract = text[start:end].strip()
                # 清理多余空行
                return re.sub(r'\n{3,}', '\n\n', abstract)
        return None

# 兼容旧代码
def parse_pdf(filepath):
    """兼容旧版API"""
    return PDFParser.parse_pdf(filepath)