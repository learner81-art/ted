import re
import pdfplumber
import requests
from io import BytesIO
from tqdm import tqdm

def parse_ted_filename(filename):
    """
    解析TED文件名格式：英文名_年份[中文名][文章内容].pdf
    返回包含英文名、年份、中文名和文章内容的字典
    """
    pattern = r'^(.*?)_(\d{4})(?:[A-Z])?\[(.*?)\]\[(.*?)\]\.pdf$|^(.*?)_(\d{4})X\[(.*?)\]\[(.*?)\]\.pdf$'
    match = re.match(pattern, filename)
    if not match:
        return None
    
    if match.lastindex == 4:  # 匹配第一种格式
        return {
            'english_name': match.group(1),
            'year': match.group(2),
            'chinese_name': match.group(3),
            'content': match.group(4)
        }
    elif match.lastindex == 8:  # 匹配第二种格式
        return {
            'english_name': match.group(5),
            'year': match.group(6),
            'chinese_name': match.group(7),
            'content': match.group(8)
        }

def extract_pdf_layout(pdf_path_or_url, max_pages=None):
    """
    新版PDF解析器：
    1. 前3页处理元数据和摘要
    2. 第4页起处理时间轴内容
    3. 严格过滤只保留中文和必要标点
    4. 去除多余空格和重复内容
    
    参数:
        pdf_path_or_url: PDF文件路径或URL
        max_pages: 可选，限制解析的最大页数
    """
    # 从URL或本地文件获取PDF
    if pdf_path_or_url.startswith('http'):
        response = requests.get(pdf_path_or_url)
        pdf_file = BytesIO(response.content)
    else:
        pdf_file = open(pdf_path_or_url, 'rb')
    
    content = {
        'summary': [],
        'translation': []
    }
    
    # 严格中文过滤正则（只保留中文和必要标点）
    chinese_filter = re.compile(r'[^\u4e00-\u9fa5，。？！、；：]')
    
    with pdfplumber.open(pdf_file) as pdf:
        page_counter = 0
        total_pages = len(pdf.pages)
        if max_pages is not None and max_pages > 0:
            total_pages = min(total_pages, max_pages)
            
        for i, page in enumerate(pdf.pages):
            if max_pages is not None and i >= max_pages:
                break
            page_counter += 1
            
            # 提取页面文本
            page_text = page.extract_text() or ""
            
            # 严格过滤非中文内容
            filtered_text = chinese_filter.sub('', page_text)
            
            # 去除多余空格和空行
            filtered_text = re.sub(r'\s+', ' ', filtered_text).strip()
            
            # 去除重复的"标题"前缀
            filtered_text = re.sub(r'标题\s*', '', filtered_text)
            
            # 处理前3页内容
            if page_counter <= 3:
                content['summary'].append(filtered_text)
                continue
                
            # 处理正文内容
            if filtered_text:
                content['translation'].append(filtered_text)
    
    if not pdf_path_or_url.startswith('http'):
        pdf_file.close()
        
    # 合并翻译内容并去除重复段落
    unique_content = []
    seen = set()
    for paragraph in content['translation']:
        if paragraph not in seen:
            seen.add(paragraph)
            unique_content.append(paragraph)
    
    content['translation'] = "\n\n".join(unique_content)
    return content

def parse_ted_file(file_path):
    """
    解析包含多个TED文件名的文本文件
    返回解析结果的列表，格式化为用户示例样式
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    
    results = []
    for line in lines:
        if line.strip():  # 跳过空行
            result = parse_ted_filename(line.strip())
            if result:
                try:
                    # 使用新的布局解析函数
                    pdf_path = f"analyze/02.历年TED文档PDF带注释/{line.strip()}"
                    content = extract_pdf_layout(pdf_path)
                    
                    # 格式化输出
                    formatted = f"""
文件名: {line.strip()}
演讲者: {result['chinese_name']}
年份: {result['year']}
主题: {result['content']}
                    概要: {"\n\n".join([f"=== 第{i+1}页 ===\n{page}" for i, page in enumerate(content['summary']) if page.strip()]).strip()}

过滤后内容:
{content['translation'].strip()}
"""
                    results.append(formatted)
                except Exception as e:
                    formatted = f"""
文件名: {line.strip()}
演讲者: {result['chinese_name']}
年份: {result['year']}
主题: {result['content']}
错误: {str(e)}
"""
                    results.append(formatted)
    
    return results

# 示例用法
if __name__ == "__main__":
    # 测试指定PDF URL
    test_url = "http://ted.source.com/AbigailDisney_2020[%E9%98%BF%E6%AF%94%E7%9B%96%E5%B0%94_%E8%BF%AA%E5%A3%AB%E5%B0%BC][%E5%B0%8A%E4%B8%A5%E4%B8%8D%E6%98%AF%E7%89%B9%E6%9D%83_%E8%80%8C%E6%98%AF%E5%8A%B3%E5%8A%A8%E8%80%85%E7%9A%84%E6%9D%83%E5%8A%9B].pdf"
    content = extract_pdf_layout(test_url)
    print("=== PDF解析结果 ===")
    print("概要:", "\n".join(content['summary']).strip())
    print("\n过滤后内容:")
    print(content['translation'])
