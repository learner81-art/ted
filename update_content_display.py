import mysql.connector
from configparser import ConfigParser
import logging
import os
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logs/update_content_display.log'
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

def get_talks_without_display():
    """获取需要更新content_display的talks记录"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, content 
        FROM talks 
        WHERE (content_display IS NULL OR content_display = '') 
        AND content IS NOT NULL
    """)
    results = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return results


def process_content(content):
    """直接处理content字段内容"""
    if not content:
        return {
            'success': False,
            'error': 'Empty content'
        }
    
    # 添加HTML格式化
    content_display = """
    <style>
        .translation-block {
            margin-bottom: 10px;
        }
        .english-line {
            background-color: #f5f5f5;
            padding: 5px;
        }
        .chinese-line {
            background-color: #e9e9e9;
            padding: 5px;
        }
    </style>
    <div class='pdf-page'>
    """
    
    # 简单按行分割并格式化
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if i % 2 == 0:
            content_display += f"<div class='english-line'>{line}</div>"
        else:
            content_display += f"<div class='chinese-line'>{line}</div>"
    
    content_display += "</div>"
    
    return {
        'success': True,
        'content_display': content_display
    }

def update_talk_display(talk_id, content_display):
    """更新talks表的content_display字段"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE talks 
            SET content_display = %s 
            WHERE id = %s
        """, (content_display, talk_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"更新失败: talk_id={talk_id} - {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def save_progress(last_id):
    """保存处理进度"""
    with open('logs/update_display_progress.json', 'w') as f:
        json.dump({'last_id': last_id}, f)

def load_progress():
    """加载处理进度"""
    if os.path.exists('logs/update_display_progress.json'):
        with open('logs/update_display_progress.json', 'r') as f:
            return json.load(f).get('last_id')
    return None

def process_single_talk(talk_id):
    """处理单条talk记录"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, content 
        FROM talks 
        WHERE id = %s
    """, (talk_id,))
    talk = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not talk:
        logging.error(f"未找到talk记录: id={talk_id}")
        return False
    
    result = process_content(talk['content'])
    if not result['success']:
        return False
    
    return update_talk_display(talk_id, result['content_display'])

def process_all_talks():
    """批量处理所有需要更新的talks记录"""
    talks = get_talks_without_display()
    if not talks:
        logging.info("没有需要更新的talks记录")
        return
    
    last_id = load_progress()
    if last_id:
        talks = [t for t in talks if t['id'] > last_id]
    
    for talk in talks:
        logging.info(f"开始处理talk: id={talk['id']}")
        
        result = process_content(talk['content'])
        if not result['success']:
            continue
            
        if update_talk_display(talk['id'], result['content_display']):
            logging.info(f"成功更新talk: id={talk['id']}")
            save_progress(talk['id'])
        else:
            logging.error(f"更新失败: id={talk['id']}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='更新talks表的content_display字段')
    parser.add_argument('--id', type=int, help='指定要更新的单个talk ID')
    args = parser.parse_args()
    
    if args.id:
        if process_single_talk(args.id):
            print(f"成功更新talk: id={args.id}")
        else:
            print(f"更新失败: id={args.id}")
    else:
        process_all_talks()
