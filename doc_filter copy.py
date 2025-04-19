import re
import pdfplumber
import requests
import os
import tempfile
from urllib.parse import unquote
from collections import defaultdict

def download_pdf(url):
    """下载PDF文件到临时目录"""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    temp_dir = tempfile.gettempdir()
    filename = url.split('/')[-1]
    filepath = os.path.join(temp_dir, filename)
    
    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return filepath

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

def filter_pdf_content(pdf_url):
    """过滤PDF内容，按颜色分类为单词区域、中文和英文内容"""
    # 下载PDF到本地
    local_pdf = download_pdf(pdf_url)
    
    try:
        meta = parse_ted_filename(pdf_url.split('/')[-1])
        
        # 匹配中文的正则
        #chinese_pattern = re.compile(r'([\u4e00-\u9fa5，。、；：？！""''"”‘’（）【】…—《》〈〉]+)')
        
        result = {
            'metadata': meta,
            'chinese': [],    # 中文纯文本
            'english': [],    # 英文内容
            'current_english': '',     # 临时存储英文内容
            'current_chinese': '',    # 临时存储中文内容
            'color_stats': defaultdict(int)  # 新增颜色统计
        }
        
        with pdfplumber.open(local_pdf) as pdf:
            for page in pdf.pages:
                for char in page.chars:
                    # 获取颜色信息
                    color = char.get("non_stroking_color", None)
                    r, g, b = round(color[0], 2), round(color[1], 2), round(color[2], 2) if color else (0, 0, 0)
                    
                    # 过滤掉绿色版权信息
                    if (r, g, b) == (0, 0.39, 0):
                        continue
                    
                    # 统计颜色
                    color = char.get("non_stroking_color", (0, 0, 0))
                    color_type = get_color_type(*color)
                    result['color_stats'][color_type] += 1
                    
                    # 处理中文内容(黑色或未标记)
                    if re.search(r'[\u4e00-\u9fa5，。、；：？！“”‘’（）【】…—《》〈〉·]', char["text"]):
                        result['current_chinese'] += char["text"]
                        continue
                    
                    # 处理英文内容 - 直接输出文本，不添加颜色标记
                    result['current_english'] += char["text"]
                
                # 保存当前页内容
                if result['current_chinese']:
                    # 只过滤英文和数字
                    chinese_text = re.sub(r'[a-zA-Z0-9]', '', result['current_chinese'])
                    # 过滤时间标记
                    chinese_text = re.sub(r'\[\d{2}:\d{2}\]', '', chinese_text)
                    # 保留原始换行和段落结构
                    if chinese_text.strip():
                        result['chinese'].append(chinese_text)
                    result['current_chinese'] = ''
                
                if result['current_english']:
                    # 处理英文文本：仅过滤时间信息和特殊字符，保留原始空格
                    english_text = re.sub(r'\[\d{2}:\d{2}\]', '', result['current_english'])  # 过滤时间信息
                    english_text = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5\s\.,;:?!""''"”‘’（）【】…—《》〈〉·-]', '', english_text)  # 保留所有字母、数字和标点
                    english_text = re.sub(r'\s+', ' ', english_text).strip()  # 标准化多余空格
                    if english_text:
                        result['english'].append(english_text)
                    result['current_english'] = ''
        
        return result
    finally:
        # 清理临时文件
        if os.path.exists(local_pdf):
            os.remove(local_pdf)

def parse_ted_filename(filename):
    """解析TED文件名格式获取元数据"""
    pattern = r'^(.*?)_(\d{4})(?:[A-Z])?\[(.*?)\]\[(.*?)\]\.pdf$'
    match = re.match(pattern, filename)
    if not match:
        return None
    return {
        'english_name': match.group(1),
        'year': match.group(2),
        'chinese_name': unquote(match.group(3)),
        'content': unquote(match.group(4))
    }

def save_filtered_result(pdf_url, output_path):
    """处理PDF并保存分类结果"""
    result = filter_pdf_content(pdf_url)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # 写入元信息
        f.write("=== 元信息 ===\n")
        f.write(f"文件名: {pdf_url.split('/')[-1]}\n")
        f.write(f"英文名: {result['metadata']['english_name']}\n")
        f.write(f"中文名: {result['metadata']['chinese_name']}\n")
        f.write(f"年份: {result['metadata']['year']}\n")
        f.write(f"主题: {result['metadata']['content']}\n\n")
        
        # 写入中文内容
        f.write("=== 中文内容 ===\n")
        for paragraph in result['chinese']:
            f.write(f"{paragraph}\n\n")
        
        # 写入英文内容
        f.write("=== 英文内容 ===\n")
        for paragraph in result['english']:
            f.write(f"{paragraph}\n\n")
            
        # 写入颜色统计
        f.write("=== 颜色统计 ===\n")
        for color, count in sorted(result['color_stats'].items(), key=lambda x: x[1], reverse=True):
            f.write(f"{color}: {count}\n")

def test_chinese_punctuation():
    """测试中文标点符号保留情况"""
    test_text = "测试文本：包含，中文标点、；：？！“”‘’（）【】…—《》〈〉·和空格-"
    filtered = re.sub(r'[^\u4e00-\u9fa5，。、；：？！“”‘’（）【】…—《》〈〉·\s-]', '', test_text)
    print("测试结果:", filtered)
    return filtered == test_text  # 应该返回True

if __name__ == "__main__":
    if test_chinese_punctuation():
        pdf_url = "http://ted.source.com/AbigailDisney_2020[%E9%98%BF%E6%AF%94%E7%9B%96%E5%B0%94_%E8%BF%AA%E5%A3%AB%E5%B0%BC][%E5%B0%8A%E4%B8%A5%E4%B8%8D%E6%98%AF%E7%89%B9%E6%9D%83_%E8%80%8C%E6%98%AF%E5%8A%B3%E5%8A%A8%E8%80%85%E7%9A%84%E6%9D%83%E5%8A%9B].pdf"
        output_file = "AbigailDisney_2020_过滤结果.txt"
        save_filtered_result(pdf_url, output_file)
        print(f"处理完成，结果已保存到 {output_file}")
    else:
        print("错误：中文标点符号测试失败，请检查正则表达式")
