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

def is_chinese(text):
    """检查文本是否包含中文字符"""
    return any('\u4e00' <= char <= '\u9fff' for char in text)

def separate_sentences(text):
    """分离中英文句子并返回两个平行数组"""
    # 预处理：保留颜色标记，移除单词解释
    text = re.sub(r'\s*\[n\..*?\]\s*', '', text)  # 过滤单词解释
    
    sentences = []
    current_en = []
    current_zh = []
    
    # 分割段落并处理
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # 跳过单词解释行（如 culture [n.文化]）
        if re.match(r'^\w+\s*\[[^\]\d:]+\]$', line):
            continue
        
        # 增强版对齐处理（带时间戳）
        # 匹配中英文组合格式（例如："What's the purpose of a company? 一个公司的目标是什么？[00:12:34]"）
        timestamp_match = re.search(r'(\[\d{2}:\d{2}:\d{2}\])$', line)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
            # 分割中英文部分
            main_part = line.replace(timestamp, '')
            split_part = re.split(r'([\u4e00-\u9fff]+)', main_part)
            if len(split_part) >= 3:
                # 更精确的分割处理
                en_part = re.sub(r'<[^>]+>', '', split_part[0]).strip()
                zh_part = re.sub(r'<[^>]+>', '', split_part[1]).strip()
                
                # 确保时间戳附加到两个版本
                en_part += ' ' + timestamp
                zh_part += ' ' + timestamp
                if en_part and zh_part:
                    current_en.append(en_part)
                    current_zh.append(zh_part)
                    continue

        # 处理无时间戳的中英文混合段落
        if '[' in line and ']' in line:
            # 增强分割逻辑（支持中英文任意顺序）
            # 改进的混合段落处理（支持任意顺序的中英文）
            split_pattern = r'(\[.*?\])([^[]*[\u4e00-\u9fff]+[^[]*)'
            matches = re.findall(split_pattern, line)
            if matches:
                for en, zh in matches:
                    current_en.append(en.strip())
                    current_zh.append(zh.strip())
                continue

        # 最终处理：确保中英文数组长度一致
        if is_chinese(line):
            # 清理中文段落中的残留标记
            clean_line = re.sub(r'<[^>]+>', '', line).strip()
            if clean_line:
                current_zh.append(clean_line)
                current_en.append("") if len(current_zh) > len(current_en) else None
        else:
            # 清理英文段落中的残留标记
            clean_line = re.sub(r'<[^>]+>', '', line).strip()
            if clean_line:
                current_en.append(clean_line)
                current_zh.append("") if len(current_en) > len(current_zh) else None
    
    # 创建平行数组
    return current_en, current_zh
    

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
            
            # 分离和处理句子，返回(english, chinese)元组
            english, chinese = separate_sentences(full_text)
            content['sentences'] = (english, chinese)
            
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
