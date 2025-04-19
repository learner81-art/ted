#!/usr/bin/env python3
import requests
import pdfplumber
from io import BytesIO
import re
import sys
from urllib.parse import unquote

def download_pdf(url):
    """下载PDF文件并返回文件对象"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        return BytesIO(response.content)
    except requests.exceptions.RequestException as e:
        print(f"下载PDF失败: {e}", file=sys.stderr)
        return None

def extract_pdf_content(pdf_file):
    """从PDF文件中提取内容"""
    content = {
        'metadata': {},
        'pages': []
    }
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            # 提取元数据
            content['metadata'] = {
                'author': pdf.metadata.get('Author'),
                'title': pdf.metadata.get('Title'),
                'pages': len(pdf.pages)
            }
            
            # 逐页提取文本
            for i, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        # 清理文本
                        page_text = re.sub(r'\s+', ' ', page_text).strip()
                        content['pages'].append({
                            'page_number': i + 1,
                            'content': page_text
                        })
                except Exception as e:
                    print(f"解析第{i+1}页时出错: {e}", file=sys.stderr)
                    continue
                    
    except Exception as e:
        print(f"解析PDF时出错: {e}", file=sys.stderr)
        return None
        
    return content

def parse_ted_url(url):
    """解析TED URL中的信息"""
    pattern = r'http://ted.source.com/(.*?)_(\d{4})\[(.*?)\]\[(.*?)\]\.pdf'
    match = re.match(pattern, url)
    if match:
        return {
            'speaker_en': match.group(1),
            'year': match.group(2),
            'speaker_zh': match.group(3),
            'title_zh': match.group(4)
        }
    return None

def main():
    # 目标PDF URL
    pdf_url = "http://ted.source.com/AbigailDisney_2020[%E9%98%BF%E6%AF%94%E7%9B%96%E5%B0%94_%E8%BF%AA%E5%A3%AB%E5%B0%BC][%E5%B0%8A%E4%B8%A5%E4%B8%8D%E6%98%AF%E7%89%B9%E6%9D%83_%E8%80%8C%E6%98%AF%E5%8A%B3%E5%8A%A8%E8%80%85%E7%9A%84%E6%9D%83%E5%8A%9B].pdf"
    
    # 解析URL信息
    url_info = parse_ted_url(pdf_url)
    if not url_info:
        print("无法解析URL格式", file=sys.stderr)
        return
    
    # 解码URL编码的中文
    speaker_zh = unquote(url_info['speaker_zh'])
    title_zh = unquote(url_info['title_zh'])
    
    print(f"开始解析: {speaker_zh} {url_info['year']}年演讲")
    print(f"主题: {title_zh}")
    
    # 下载PDF
    pdf_file = download_pdf(pdf_url)
    if not pdf_file:
        return
    
    # 提取内容
    content = extract_pdf_content(pdf_file)
    if not content:
        return
    
    # 输出结果
    output = f"""=== PDF解析结果 ===
演讲者: {speaker_zh} ({url_info['speaker_en']})
年份: {url_info['year']}
主题: {title_zh}
页数: {content['metadata']['pages']}

=== 内容摘要 ===
"""
    
    for page in content['pages']:
        output += f"\n第{page['page_number']}页:\n{page['content']}\n"
    
    # 保存到文件
    output_file = f"{url_info['speaker_en']}_{url_info['year']}_解析结果.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"解析完成，结果已保存到: {output_file}")

if __name__ == "__main__":
    main()
