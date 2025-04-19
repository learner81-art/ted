import re
import pdfplumber
import requests
import os
import tempfile
import nltk
from urllib.parse import unquote
from collections import defaultdict
from nltk.tokenize import word_tokenize, sent_tokenize

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

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

def process_page(page, meta):
    """处理单页PDF内容"""
    page_result = {
        'chinese': [],
        'english': [],
        'word_zone': [],
        'current_english': '',
        'current_chinese': '',
        'current_word_zone': '',
        'colored_words': {'red': set(), 'blue': set()},
        'color_stats': defaultdict(int)
    }
    
    try:
        chars = page.chars
    except Exception as e:
        print(f"警告: 无法获取页面字符 - {str(e)}")
        return page_result
    
    for char in chars:
        # 获取颜色信息
        color = char.get("non_stroking_color", None)
        r, g, b = round(color[0], 2), round(color[1], 2), round(color[2], 2) if color else (0, 0, 0)
        
        # 过滤掉绿色版权信息
        if (r, g, b) == (0, 0.39, 0):
            continue
        
        # 统计颜色
        color = char.get("non_stroking_color", (0, 0, 0))
        color_type = get_color_type(*color)
        page_result['color_stats'][color_type] += 1
        
        # 处理中文内容(黑色或未标记)
        if re.search(r'[\u4e00-\u9fa5，。、；：？！""''"”‘’（）【】…—《》〈〉·]', char["text"]):
            page_result['current_chinese'] += char["text"]
            continue
        
        # 处理英文内容 - 仅过滤中文和数字
        text = char["text"]
        text = re.sub(r'[\u4e00-\u9fa50-9]', '', text)
        if text:  # 如果过滤后不为空
            # 收集当前字符到英文内容
            page_result['current_english'] += text
            
            # 检测单词边界(空格或标点)
            if not text.isalpha():
                # 如果当前收集的英文内容包含完整单词
                if page_result['current_english'].strip():
                    # 检查最后一个字符是否是单词分隔符
                    last_word = re.findall(r'[a-zA-Z]+', page_result['current_english'])
                    if last_word:
                        last_word = last_word[-1]
                        # 根据颜色标记单词
                        if color_type == 'red':
                            if not page_result['current_word_zone']:
                                page_result['colored_words']['red'].add(last_word)
                        elif color_type == 'blue':
                            if not page_result['current_word_zone']:
                                page_result['colored_words']['blue'].add(last_word)
    
    # 保存当前页内容
    if page_result['current_chinese']:
        chinese_text = re.sub(r'[a-zA-Z0-9]', '', page_result['current_chinese'])
        chinese_text = re.sub(r'\[\d{2}:\d{2}\]', '', chinese_text)
        if chinese_text.strip():
            page_result['chinese'].append(chinese_text)
        page_result['current_chinese'] = ''
    
    if page_result['current_english']:
        english_text = page_result['current_english']
        if english_text.strip():
            page_result['english'].append(english_text)
        page_result['current_english'] = ''
    
        # 检测单词区域结束(当遇到英文短句开始时)
        if page_result['colored_words'] and len(page_result['current_word_zone']) > 50:
                # 输出去重后的单词列表
                if page_result['colored_words']['red'] or page_result['colored_words']['blue']:
                    red_words = " ".join(page_result['colored_words']['red'])
                    blue_words = " ".join(page_result['colored_words']['blue'])
                    if red_words or blue_words:
                        page_result['word_zone'].append(f"红色单词: {red_words}\n蓝色单词: {blue_words}")
                    page_result['colored_words'] = {'red': set(), 'blue': set()}
    
    return page_result

def filter_pdf_content(pdf_url):
    """过滤PDF内容，按颜色分类为单词区域、中文和英文内容"""
    # 下载PDF到本地
    local_pdf = download_pdf(pdf_url)
    
    try:
        meta = parse_ted_filename(pdf_url.split('/')[-1])
        result = {
            'metadata': meta,
            'chinese': [],
            'english': [],
            'word_zone': [],
            'colored_words': {'red': set(), 'blue': set()},  # 按颜色分类存储单词
            'color_stats': defaultdict(int)
        }
        
        with pdfplumber.open(local_pdf) as pdf:
            for page in pdf.pages:
                page_result = process_page(page, meta)
                result['chinese'].extend(page_result['chinese'])
                result['english'].extend(page_result['english'])
                result['word_zone'].extend(page_result['word_zone'])
                # 合并红色单词
                result['colored_words']['red'].update(page_result['colored_words']['red'])
                # 合并蓝色单词
                result['colored_words']['blue'].update(page_result['colored_words']['blue'])
                for color, count in page_result['color_stats'].items():
                    result['color_stats'][color] += count
        
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

def summarize_text(text):
    """生成最简洁中文摘要"""
    sentences = sent_tokenize(text)
    if not sentences:
        return ""
        
    # 提取所有包含中文的句子
    chinese_sentences = [
        s.strip() for s in sentences 
        if any('\u4e00' <= char <= '\u9fff' for char in s)
    ]
    
    if not chinese_sentences:
        return "未能提取有效摘要"
        
    # 按句子长度排序(从短到长)
    chinese_sentences.sort(key=len)
    
    # 返回最短的3个中文句子，用句号连接
    summary = "。".join(chinese_sentences[:3])
    if len(summary) > 300:  # 如果太长则截取前300字符
        summary = summary[:300] + "..."
    
    return summary

def clean_text(text):
    """应用二次过滤清理文本"""
    color_pattern = re.compile(r'\[r=[^\]]+\]')  # 匹配所有颜色标记
    explanation_pattern = re.compile(r'\[:[^\]]+\]')  # 匹配所有单词解释
    special_chars = re.compile(r'[^\w\s\u4e00-\u9fa5，。、；：？！（）《》【】]')  # 保留中英文和常见标点
    
    cleaned = color_pattern.sub('', text)  # 移除颜色标记
    cleaned = explanation_pattern.sub('', cleaned)  # 移除单词解释
    cleaned = special_chars.sub('', cleaned)  # 移除特殊字符
    
    # 处理英文单词分词
    if any(char.isalpha() for char in cleaned):
        tokens = word_tokenize(cleaned)
        cleaned = ' '.join(tokens)
    
    return cleaned

def save_filtered_result(pdf_url, output_path):
    """处理PDF并保存分类结果"""
    result = filter_pdf_content(pdf_url)
    full_text = []
    
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
            cleaned = clean_text(paragraph)
            if cleaned.strip():
                f.write(f"{cleaned}\n\n")
                full_text.append(cleaned)
        
        # 写入英文内容
        f.write("=== 英文内容 ===\n")
        for paragraph in result['english']:
            cleaned = clean_text(paragraph)
            if cleaned.strip():
                f.write(f"{cleaned}\n\n")
                full_text.append(cleaned)
        
        # 写入单词区域
        f.write("=== 单词区域 ===\n")
        if result['word_zone']:
            cleaned_zones = [clean_text(zone) for zone in result['word_zone']]
            f.write("\n".join(cleaned_zones) + "\n\n")
            full_text.extend(cleaned_zones)
            
        # 写入红色单词
        f.write("=== 红色单词 ===\n")
        if result['colored_words']['red']:
            cleaned_red = clean_text(", ".join(sorted(result['colored_words']['red'])))
            f.write(f"{cleaned_red}\n\n")
            full_text.append(cleaned_red)
            
        # 写入蓝色单词
        f.write("=== 蓝色单词 ===\n")
        if result['colored_words']['blue']:
            cleaned_blue = clean_text(", ".join(sorted(result['colored_words']['blue'])))
            f.write(f"{cleaned_blue}\n\n")
            full_text.append(cleaned_blue)
            
        # 写入颜色统计
        f.write("=== 颜色统计 ===\n")
        for color, count in sorted(result['color_stats'].items(), key=lambda x: x[1], reverse=True):
            f.write(f"{color}: {count}\n")
        
        # 写入摘要
        f.write("\n=== 内容摘要 ===\n")
        summary = summarize_text("\n".join(full_text))
        f.write(summary + "\n")

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
