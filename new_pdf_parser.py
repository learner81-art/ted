#!/usr/bin/env python3
import requests
import pdfplumber
from io import BytesIO
import re
import sys
import langid
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

def is_chinese(text):
    """检查文本是否包含中文字符"""
    return any('\u4e00' <= char <= '\u9fff' for char in text)

def classify_language(text):
    """使用langid进行语言分类"""
    lang, confidence = langid.classify(text)
    return 'zh' if lang == 'zh' and confidence > 0.8 else 'en'

def split_sentences(text, language):
    """根据语言分句"""
    if language == 'zh':
        return [s.strip() for s in re.findall(r'.*?[。！？]+(?=\s|$)', text)]
    else:
        return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text)]

def separate_sentences(text):
    """提取纯中文内容并过滤非中文字符"""
    chinese_paragraphs = []
    current_para = []
    
    # 保留中文及标点的正则表达式
    keep_pattern = re.compile(
        r'([\u4e00-\u9fff]'  # 中文字符
        r'|[\u3000-\u303F]'  # 中文标点符号
        r'|[\uFF00-\uFFEF]'  # 全角符号
        r'|[\u2010-\u2015]'  # 连字符
        r'|[\u2026]'         # 省略号
        r'|[\u00B7])+')      # 间隔号
    
    # 提取中文内容（包含标点）
    chinese_blocks = keep_pattern.findall(text)
    
    # 合并相邻的中文块
    merged_text = ' '.join(chinese_blocks)
    
    # 使用改进的分句逻辑
    sentences = re.split(r'([。！？])', merged_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # 重组句子（保留标点）
    chinese_paragraphs = []
    for i in range(0, len(sentences)-1, 2):
        chinese_paragraphs.append(sentences[i] + sentences[i+1])
    
    # 返回结构化数据（英文在前，中文在后）
    return [], chinese_paragraphs
    

def extract_pdf_content(pdf_file):
    """从PDF文件中提取内容"""
    content = {
        'metadata': {},
        'sentences': []
    }
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            # 提取元数据
            content['metadata'] = {
                'author': pdf.metadata.get('Author'),
                'title': pdf.metadata.get('Title'),
                'pages': len(pdf.pages)
            }
            
            # 提取并处理正文内容
            full_text = ""
            for page in pdf.pages:
                try:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += re.sub(r'\s+', ' ', page_text).strip() + " "
                except Exception as e:
                    print(f"解析页面时出错: {e}", file=sys.stderr)
                    continue
            
            # 预处理并处理段落
            english_paragraphs, chinese_paragraphs = separate_sentences(full_text)
            
            # 创建结构化内容
            content['sentences'] = (
                [s for para in english_paragraphs for s in split_sentences(para, 'en')],  # 英文句子数组
                chinese_paragraphs  # 直接使用中文段落数组
            )
            
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
    output = f"""=== PDF元数据 ===
演讲者: {speaker_zh} ({url_info['speaker_en']})
年份: {url_info['year']}
主题: {title_zh}
页数: {content['metadata']['pages']}

=== 中英文对照内容 ===
"""
    
    # 输出结构化数组格式
    output += "\n[eng]"
    for i, en in enumerate(content['sentences'][0]):
        output += f"\n[{i}] {en}"
    
    output += "\n\n[chinese]"
    for i, zh in enumerate(content['sentences'][1]):
        output += f"\n[{i}] {zh}"
    
    # 保存到文件
    output_file = f"{url_info['speaker_en']}_{url_info['year']}_解析结果.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"解析完成，结果已保存到: {output_file}")

if __name__ == "__main__":
    main()
