import mysql.connector
from typing import Dict

# MySQL连接配置 (与speakers_web.py一致)
DB_CONFIG = {
    'host': 'localhost',
    'port': '3306',
    'user': 'root',
    'password': 'root',
    'database': 'ted_talks_db',
    'ssl_disabled': True
}

def parse_content(content: str) -> Dict:
    """解析content字段内容"""
    # 处理content字段 - 截取"内容概要："之后的内容
    processed_content = content
    colon_patterns = ['内容概要：', '内容概要：', 'Summary：', 'Summary:']
    for pattern in colon_patterns:
        if pattern in content:
            processed_content = content.split(pattern, 1)[1].strip()
            break
            
    result = {
        'speaker': '',
        'title': '',
        'summary': '',
        'detail': '',
        'content': processed_content
    }
    
    # 提取演讲者（支持多种格式）
    speaker_patterns = ['演讲者：', '演讲者:', 'Speaker:', 'Speaker：']
    for pattern in speaker_patterns:
        if pattern in content:
            result['speaker'] = content.split(pattern)[1].split('\n')[0].strip()
            break
    
    # 提取标题（支持多种格式）
    title_patterns = ['标题：', '标题:', 'Title:', 'Title：']
    for pattern in title_patterns:
        if pattern in content:
            result['title'] = content.split(pattern)[1].split('\n')[0].strip()
            break
    
    # 分割概要和详情（支持多种分隔符）
    split_patterns = ['锡育软件', '内容详情：', 'Details:']
    for pattern in split_patterns:
        if pattern in content:
            parts = content.split(pattern)
            result['summary'] = parts[0].strip()
            result['detail'] = pattern + ' ' + parts[1].strip() if len(parts) > 1 else ''
            break
    
    # 如果没有找到分隔符，整个内容作为详情
    if not result['detail'] and content:
        result['detail'] = content
    
    return result

def test_content_split(limit=5):
    """测试内容分拆功能"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, content FROM talks LIMIT %s", (limit,))
        
        for row in cursor:
            print(f"\n=== 解析演讲ID {row['id']} ===")
            parsed = parse_content(row['content'])
            print(f"演讲者: {parsed['speaker']}")
            print(f"标题: {parsed['title']}")
            print("内容概要:")
            print(parsed['summary'])
            print("内容详情:")
            print(parsed['detail'])
            print("-" * 50)
            
    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    test_content_split()
