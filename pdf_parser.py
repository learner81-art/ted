import re
import PyPDF2
from io import BytesIO
import requests

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

def generate_summary(pdf_content):
    """
    从PDF内容生成简单摘要
    这里只是一个示例实现，实际应用中可以使用更复杂的NLP技术
    """
    # 简单提取前200个字符作为摘要
    text = pdf_content[:200].replace('\n', ' ')
    if len(text) == 200:
        text += "..."
    return text

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
                # 尝试读取PDF内容
                try:
                    with open(f"analyze/02.历年TED文档PDF带注释/{line.strip()}", 'rb') as pdf_file:
                        reader = PyPDF2.PdfReader(pdf_file)
                        pdf_content = ""
                        for page in reader.pages:
                            pdf_content += page.extract_text()
                        
                        summary = generate_summary(pdf_content)
                except Exception as e:
                    summary = "待定"
                
                # 格式化输出
                formatted = f"""
文件名: {line.strip()}
演讲者: {result['chinese_name']}
年份: {result['year']}
主题: {result['content']}
总结: {summary}
"""
                results.append(formatted)
    
    return results

# 示例用法
if __name__ == "__main__":
    # 测试整个文件
    results = parse_ted_file("analyze/02.历年TED文档PDF带注释/TED_analysis.txt")
    for result in results[:1]:  # 只打印第一个结果作为示例
        print(result)
