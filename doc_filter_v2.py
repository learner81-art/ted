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
        
        result = {
            'metadata': meta,
            'chinese': [],    # 中文纯文本
            'english': [],    # 英文内容
            'vocabulary': [], # 单词区域
            'current_english': '',     # 临时存储英文内容
            'current_chinese': '',    # 临时存储中文内容
            'current_vocab': '',      # 临时存储单词区域
            'color_stats': defaultdict(int),  # 颜色统计
            'colored_words': []       # 存储标红标蓝单词
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
                    
                    # 处理标红标蓝单词
                    if color_type in ['red', 'blue']:
                        result['colored_words'].append({
                            'text': char["text"],
                            'color': color_type
                        })
                    
                    # 处理中文内容(黑色或未标记)
                    if re.search(r'[\u4e00-\u9fa5，。、；：？！""''"”‘’（）【】…—《》〈〉·]', char["text"]):
                        result['current_chinese'] += char["text"]
                        continue
                    
                    # 处理英文内容 - 仅过滤中文和数字
                    text = char["text"]
                    text = re.sub(r'[\u4e00-\u9fa50-9]', '', text)
                    if text:  # 如果过滤后不为空
                        result['current_english'] += text
                
                # 保存当前页内容
                if result['current_chinese']:
                    chinese_text = re.sub(r'[a-zA-Z0-9]', '', result['current_chinese'])
                    chinese_text = re.sub(r'\[\d{2}:\d{2}\]', '', chinese_text)
                    if chinese_text.strip():
                        result['chinese'].append(chinese_text)
                    result['current_chinese'] = ''
                
                if result['current_english']:
                    english_text = result['current_english']
                    if english_text.strip():
                        result['english'].append(english_text)
                    result['current_english'] = ''
                
                # 处理单词区域 - 只着色英文单词，保留中文和分隔符
                if result['colored_words']:
                    vocab_text = ''
                    current_word = ''
                    current_color = None
                    
                    for word in result['colored_words']:
                        # 如果是英文字母，添加到当前单词
                        if word['text'].isalpha():
                            if current_color is None or current_color != word['color']:
                                if current_word:
                                    vocab_text += f"<{current_color}>{current_word}</{current_color}>"
                                    current_word = ''
                                current_color = word['color']
                            current_word += word['text']
                        else:
                            # 非字母字符，输出当前单词(如果有)和当前字符
                            if current_word:
                                vocab_text += f"<{current_color}>{current_word}</{current_color}>"
                                current_word = ''
                            vocab_text += word['text']
                    
                    # 处理最后一个单词
                    if current_word:
                        vocab_text += f"<{current_color}>{current_word}</{current_color}>"
                    
                    result['vocabulary'].append(vocab_text)
                    result['colored_words'] = []
        
        return result
    finally:
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
        
        # 写入英文内容(带红蓝标记)
        f.write("=== 英文内容 ===\n")
        for paragraph in result['english']:
            # 添加红蓝标记 - 按单词标记
            marked_paragraph = ''
            words = re.findall(r"([a-zA-Z]+|[^a-zA-Z]+)", paragraph)
            
            for word in words:
                if word.isalpha():  # 只处理字母组成的单词
                    # 查找单词中第一个字符的颜色
                    first_char = word[0]
                    color = None
                    for c in result['colored_words']:
                        if c['text'] == first_char:
                            color = c['color']
                            break
                    
                    if color:
                        marked_paragraph += f"<{color}>{word}</{color}>"
                    else:
                        marked_paragraph += word
                else:  # 非字母部分原样保留
                    marked_paragraph += word
            f.write(f"{marked_paragraph}\n\n")
        
        # 写入单词区域
        f.write("=== 单词区域 ===\n")
        for vocab in result['vocabulary']:
            f.write(f"{vocab}\n\n")
            
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
