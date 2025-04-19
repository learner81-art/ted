import pdfplumber
import tempfile
import requests
import os
from collections import defaultdict

def download_pdf(url):
    """下载PDF文件"""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    temp_dir = tempfile.gettempdir()
    filename = url.split('/')[-1]
    filepath = os.path.join(temp_dir, filename)
    
    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return filepath

def is_chinese(char):
    """检查字符是否为中文"""
    return '\u4e00' <= char <= '\u9fff'

def get_color_type(r, g, b):
    """根据RGB值返回颜色类型"""
    r, g, b = round(r, 2), round(g, 2), round(b, 2)
    
    # 黑色 (非红非蓝)
    if r == 0.00 and g == 0.00 and b == 0.00:
        return "black"
    # 蓝色 (b值最高)
    elif b >= 0.55 and b > max(r, g):
        return "blue"
    # 绿色 (g值最高)
    elif g >= 0.39 and g > max(r, b):
        return "green" 
    # 红色 (r值最高)
    elif r >= 0.50 and r > max(g, b):
        return "red"
    # 深灰色 (非红非蓝)
    elif 0.14 <= r <= 0.15 and 0.14 <= g <= 0.15 and 0.14 <= b <= 0.15:
        return "dark_gray"
    else:
        return "other"

def analyze_page_colors(pdf_url, page_num=2):
    """分析PDF指定页面的颜色统计"""
    local_pdf = download_pdf(pdf_url)
    stats = {
        "text_colors": defaultdict(list),  # 文字颜色单词列表
        "bg_colors": defaultdict(int),    # 背景色统计
        "total_words": 0,
        "chinese_chars": 0
    }
    
    try:
        with pdfplumber.open(local_pdf) as pdf:
            if len(pdf.pages) < page_num:
                raise ValueError(f"PDF只有{len(pdf.pages)}页，无法分析第{page_num}页")
                
            page = pdf.pages[page_num-1]
            words = page.extract_words(extra_attrs=["non_stroking_color", "stroking_color"])
            
            for word in words:
                # 统计中英文字符
                has_chinese = any(is_chinese(c) for c in word['text'])
                if has_chinese:
                    stats["chinese_chars"] += len(word['text'])
                
                stats['total_words'] += 1
                
                # 分析文字颜色 (使用non_stroking_color)
                text_color = word.get("non_stroking_color", (0, 0, 0))
                r, g, b = text_color
                color_type = get_color_type(r, g, b)
                stats["text_colors"][color_type].append(word['text'])  # 记录单词本身
                
                # 分析背景色 (使用stroking_color)
                bg_color = word.get("stroking_color", (1, 1, 1))  # 默认白色背景
                r, g, b = bg_color
                bg_type = get_color_type(r, g, b)
                stats["bg_colors"][bg_type] += 1
                
    
    finally:
        if os.path.exists(local_pdf):
            os.remove(local_pdf)
    
    # 输出结果
    with open('page_color_stats.txt', 'w', encoding='utf-8') as f:
        f.write(f"=== PDF第{page_num}页颜色统计 ===\n")
        f.write(f"总单词数: {stats['total_words']}\n")
        f.write(f"中文字符数: {stats['chinese_chars']}\n\n")
        
        f.write("背景颜色统计:\n")
        for color, count in stats["bg_colors"].items():
            f.write(f"{color}: {count} 处\n")
            
        f.write("\n文字颜色统计(按单词):\n")
        for color, words in stats["text_colors"].items():
            f.write(f"\n{color} ({len(words)} 单词):\n")
            f.write(", ".join(words) + "\n")
        
    
    return stats

if __name__ == "__main__":
    pdf_url = "http://ted.source.com/AbigailDisney_2020[%E9%98%BF%E6%AF%94%E7%9B%96%E5%B0%94_%E8%BF%AA%E5%A3%AB%E5%B0%BC][%E5%B0%8A%E4%B8%A5%E4%B8%8D%E6%98%AF%E7%89%B9%E6%9D%83_%E8%80%8C%E6%98%AF%E5%8A%B3%E5%8A%A8%E8%80%85%E7%9A%84%E6%9D%83%E5%8A%9B].pdf"
    
    print(f"开始分析PDF第二页的颜色统计...")
    stats = analyze_page_colors(pdf_url)
    print(f"分析完成，结果已保存到 page_color_stats.txt")
    print("\n背景颜色统计:")
    for color, count in stats["bg_colors"].items():
        print(f"{color}: {count} 处")
        
    print("\n文字颜色统计(按单词):")
    for color, words in stats["text_colors"].items():
        print(f"\n{color} ({len(words)} 单词):")
        print(", ".join(words))
