import re
import pdfplumber
import requests
import os
import time
import tempfile
import nltk
import mysql.connector
from datetime import datetime
from urllib.parse import unquote
from collections import defaultdict
from nltk.tokenize import word_tokenize, sent_tokenize

# 数据库配置 (从speakers_web.py导入)
DB_CONFIG = {
    'host': 'localhost',
    'port': '3306',
    'user': 'root',
    'password': 'root',
    'database': 'ted_talks_db',
    'ssl_disabled': True
}

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

def delete_es_document(doc_id):
    """删除Elasticsearch中的文档"""
    es_url = "http://localhost:9200"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    index_name = "ted_talks"
    
    try:
        resp = requests.delete(
            f"{es_url}/{index_name}/_doc/{doc_id}",
            headers=headers
        )
        resp.raise_for_status()
        print(f"成功从Elasticsearch删除文档 {doc_id}")
    except Exception as e:
        print(f"删除Elasticsearch文档时出错: {e}")

def save_filtered_result(pdf_url, output_path, max_retries=3):
    """处理PDF并保存分类结果"""
    doc_id = pdf_url.split('/')[-1].split('.')[0]  # 使用文件名作为文档ID
    
    for attempt in range(max_retries):
            # 检查是否是特定文件卡住的情况
            # 精确匹配文件名模式
            try:
                if re.search(r'AlexGendler_FlightSpeed_2020E\[.*?\]\[.*?\]', pdf_url) and os.path.exists(output_path):
                    print(f"检测到卡住文件 {output_path}，执行强制清理...")
                    try:
                        if os.path.exists(output_path):
                            os.remove(output_path)
                            print(f"成功删除文件 {output_path}")
                        # 增加ES文档存在性检查
                        if requests.get(f"http://localhost:9200/ted_talks/_doc/{doc_id}").status_code == 200:
                            delete_es_document(doc_id)
                        # 立即重新处理当前文件
                        print("正在重新处理文件...")
                        return save_filtered_result(pdf_url, output_path, max_retries-1 if max_retries>0 else 0)
                    except Exception as e:
                        print(f"清理操作异常: {e}")
                        raise
                    finally:
                        time.sleep(2)  # 延长等待时间
            except Exception as outer_e:
                print(f"外层清理检测异常: {outer_e}")
            
            result = filter_pdf_content(pdf_url)
            full_text = []
            
            # Elasticsearch配置
            es_url = "http://localhost:9200"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            index_name = "ted_talks"
    
            # 准备Elasticsearch文档数据
            es_doc = {
                "metadata": result['metadata'],
                "chinese_content": "\n".join(result['chinese']),
                "english_content": "\n".join(result['english']),
                "word_zone": "\n".join(result['word_zone']),
                "colored_words": {
                    "red": list(result['colored_words']['red']),
                    "blue": list(result['colored_words']['blue'])
                },
                "color_stats": dict(result['color_stats']),
                "timestamp": datetime.now().isoformat()
            }
            
            # 写入Elasticsearch
            try:
                # 检查索引是否存在，不存在则创建
                resp = requests.get(f"{es_url}/{index_name}", headers=headers)
                if resp.status_code == 404:
                    settings = {
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0
                        }
                    }
                    resp = requests.put(
                        f"{es_url}/{index_name}",
                        json=settings,
                        headers=headers
                    )
                    resp.raise_for_status()
                
                # 插入文档
                resp = requests.post(
                    f"{es_url}/{index_name}/_doc/{doc_id}",
                    json=es_doc,
                    headers=headers
                )
                resp.raise_for_status()
                print(f"成功将数据写入Elasticsearch索引 {index_name}")
                break  # 成功则退出重试循环
            except Exception as e:
                print(f"写入Elasticsearch文档时出错: {e}")
                if attempt == max_retries - 1:
                    raise  # 最后一次尝试失败则抛出异常
                time.sleep(2)  # 等待后重试
    
            # 写入本地文件
            try:
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
            except Exception as e:
                print(f"写入文件 {output_path} 时出错: {e}")
                raise

def test_chinese_punctuation():
    """测试中文标点符号保留情况"""
    test_text = "测试文本：包含，中文标点、；：？！“”‘’（）【】…—《》〈〉·和空格-"
    filtered = re.sub(r'[^\u4e00-\u9fa5，。、；：？！“”‘’（）【】…—《》〈〉·\s-]', '', test_text)
    print("测试结果:", filtered)
    return filtered == test_text  # 应该返回True

def process_batch(cursor, batch_size=100, resume_from=0):
    """分批处理PDF文件，添加对特定文件的重试逻辑"""
    processed = 0
    
    try:
        # 确保查询结果被完全处理
        cursor.execute(f"SELECT pdf_url FROM speakers WHERE pdf_url IS NOT NULL LIMIT {resume_from}, {batch_size}")
        rows = cursor.fetchall()
        
        # 显式消耗结果集
        for row in rows:
            # 确保结果集被完全处理
            if cursor.with_rows:
                cursor.fetchall()
            try:
                pdf_url = row['pdf_url']
                # 从URL获取文件名并移除.pdf扩展名
                filename = os.path.basename(pdf_url).replace('.pdf', '')
                # 生成安全的输出文件名 - 替换方括号为圆括号
                safe_filename = filename.replace('[', '(').replace(']', ')')
                output_file = f"{safe_filename}_过滤结果.txt"
                
                # 检查Elasticsearch中是否已存在该文档
                es_url = "http://localhost:9200"
                doc_id = filename
                
                # 检查Elasticsearch文档是否存在
                es_resp = requests.get(f"{es_url}/ted_talks/_doc/{doc_id}", timeout=5)
                if es_resp.status_code == 200:
                    es_data = es_resp.json()
                    # 检查speakers.bio字段是否匹配最后中括号内容
                    cursor.execute("SELECT bio FROM speakers WHERE pdf_url = %s", (pdf_url,))
                    speaker_bio = cursor.fetchone()
                    # 提取doc_id最后中括号里的内容
                    bracket_content = re.search(r'\[([^]]+)\]$', doc_id)
                    bracket_content = bracket_content.group(1) if bracket_content else None
                    if speaker_bio and bracket_content and speaker_bio['bio'] == bracket_content:
                        # 检查内容是否非空
                        if es_data['_source'].get('english_content') and es_data['_source'].get('chinese_content'):
                            print(f"跳过已处理文档(ES中存在且内容完整): {filename}")
                            processed += 1
                            continue  # 继续处理下一行
                
                print(f"正在处理({resume_from + processed + 1}): {filename}")
                save_filtered_result(pdf_url, output_file)
                print(f"处理完成，结果已保存到 {output_file}")
                processed += 1
                
                # 每处理10个文件后暂停1秒
                if processed % 10 == 0:
                    time.sleep(1)
                    
            except Exception as e:
                print(f"处理 {filename} 时出错: {e}")
                # 记录错误但继续处理下一个
                with open("processing_errors.log", "a") as f:
                    f.write(f"{datetime.now()}: {filename} - {str(e)}\n")
    
    finally:
        # 确保游标被重置以释放资源
        try:
            if cursor.with_rows:
                while cursor.fetchone() is not None:
                    pass
        except mysql.connector.Error:
            pass  # 忽略已经关闭的游标错误
    
    return processed

def get_db_connection():
    """获取数据库连接"""
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"数据库连接错误: {err}")
        raise

if __name__ == "__main__":
    if not test_chinese_punctuation():
        print("错误：中文标点符号测试失败，请检查正则表达式")
        exit(1)
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 获取总记录数
        cursor.execute("SELECT COUNT(*) as total FROM speakers WHERE pdf_url IS NOT NULL")
        total = cursor.fetchone()['total']
        print(f"发现 {total} 个PDF需要处理")
        
        batch_size = 50  # 每批处理数量
        processed = 0
        
        while processed < total:
            print(f"\n=== 正在处理批次 {processed//batch_size + 1} ===")
            count = process_batch(cursor, batch_size, processed)
            processed += count
            
            # 每批处理后暂停5秒
            if count > 0 and processed < total:
                print(f"已完成 {processed}/{total}，暂停5秒...")
                time.sleep(5)
                
    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
    except KeyboardInterrupt:
        print(f"\n处理中断，已处理 {processed} 个文件")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
