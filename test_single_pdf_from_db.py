import mysql.connector
import requests
from io import BytesIO
import PyPDF2
from configparser import ConfigParser
import chardet
import logging
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logs/pdf_batch_processing.log'
)

def get_db_connection():
    """获取数据库连接"""
    config = ConfigParser()
    with open('config.ini', 'r', encoding='utf-8') as f:
        config.read_file(f)
    
    return mysql.connector.connect(
        host=config['database']['host'],
        user=config['database']['user'],
        password=config['database']['password'],
        database=config['database']['database'],
        charset='utf8mb4',
        use_unicode=True
    )

def get_all_pdf_urls():
    """从speakers表获取所有pdf_url"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, chinese_name, english_name, pdf_url 
        FROM speakers 
        WHERE pdf_url IS NOT NULL
    """)
    results = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return results

def parse_pdf_from_url(pdf_url):
    """从URL下载并解析PDF"""
    try:
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        
        with BytesIO(response.content) as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            content = ""
            content_display = ""
            for page in reader.pages:
                try:
                    text = page.extract_text()
                    if text:
                        content += text + '\n'
                        # 保留格式信息
                        content_display += f"<div class='pdf-page'>\n{text}\n</div>\n"
                except Exception as e:
                    logging.warning(f"页面解析错误: {str(e)}")
                    continue
            
            return {
                'success': True,
                'content': content,
                'content_display': content_display,
                'page_count': len(reader.pages)
            }
    except Exception as e:
        logging.error(f"PDF解析失败: {pdf_url} - {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def save_to_talks(speaker_id, speaker_name_zh, speaker_name_en, pdf_data):
    """将解析结果存入talks表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO talks (
                speaker_id, speaker_name_zh, speaker_name_en,
                pdf_url, content, content_display, page_count
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            speaker_id,
            speaker_name_zh,
            speaker_name_en,
            pdf_data['url'],
            pdf_data['content'],
            pdf_data.get('content_display', ''),
            pdf_data['page_count']
        ))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"数据库保存失败: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def process_all_pdfs():
    """批量处理所有PDF记录"""
    pdf_records = get_all_pdf_urls()
    if not pdf_records:
        logging.warning("没有找到PDF记录")
        return
    
    success_count = 0
    failure_count = 0
    
    for record in tqdm(pdf_records, desc="处理PDF文件"):
        pdf_url = record['pdf_url']
        logging.info(f"开始处理PDF: {pdf_url}")
        
        result = parse_pdf_from_url(pdf_url)
        if not result['success']:
            logging.error(f"处理失败: {pdf_url}")
            failure_count += 1
            continue
            
        pdf_data = {
            'url': pdf_url,
            'content': result['content'],
            'page_count': result['page_count']
        }
        
        if save_to_talks(
            record['id'],
            record['chinese_name'],
            record['english_name'],
            pdf_data
        ):
            logging.info(f"成功保存PDF: {pdf_url}")
            success_count += 1
        else:
            logging.error(f"保存失败: {pdf_url}")
            failure_count += 1
    
    logging.info(f"处理完成: 成功 {success_count} 个, 失败 {failure_count} 个")

def insert_test_talk():
    """插入测试数据到talks表"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取第一个speaker作为外键引用
    cursor.execute("SELECT id, chinese_name, english_name FROM speakers LIMIT 1")
    speaker = cursor.fetchone()
    
    if not speaker:
        print("错误: speakers表中没有记录，请先添加speaker数据")
        return
    
    test_data = {
        'speaker_id': speaker['id'],
        'speaker_name_zh': speaker['chinese_name'],
        'speaker_name_en': speaker['english_name'],
        'pdf_url': 'http://ted.source.com/AdongJudith_2017G[阿东_朱迪思][我如何用艺术来弥合误解].pdf',
        'content': '这是测试演讲内容',
        'content_display': '<div class="pdf-page">这是测试演讲内容</div>',
        'page_count': 10
    }
    
    try:
        cursor.execute("""
            INSERT INTO talks (
                speaker_id, speaker_name_zh, speaker_name_en,
                pdf_url, content, page_count
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            test_data['speaker_id'],
            test_data['speaker_name_zh'],
            test_data['speaker_name_en'],
            test_data['pdf_url'],
            test_data['content'],
            test_data['page_count']
        ))
        conn.commit()
        print(f"成功插入测试数据: {test_data}")
    except Exception as e:
        conn.rollback()
        print(f"插入测试数据失败: {str(e)}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # 批量处理所有PDF记录
    process_all_pdfs()
#test hook