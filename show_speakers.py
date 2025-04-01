import mysql.connector
from tabulate import tabulate

# 使用与insert_speakers.py相同的数据库配置
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'root',
    'database': 'ted_talks_db'
}

def fetch_speakers(limit=20):
    """从数据库获取演讲者数据"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT english_name, chinese_name, profession, 
               organization, bio 
        FROM speakers
        LIMIT %s
        """
        cursor.execute(query, (limit,))
        return cursor.fetchall()
        
    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def display_speakers(speakers):
    """以表格形式展示演讲者数据"""
    if not speakers:
        print("没有找到演讲者数据")
        return
    
    # 准备表格数据
    table_data = []
    headers = ["英文名", "中文名", "职业", "组织", "简介"]
    
    for speaker in speakers:
        table_data.append([
            speaker['english_name'],
            speaker['chinese_name'],
            speaker['profession'],
            speaker['organization'],
            speaker['bio'][:50] + '...' if speaker['bio'] and len(speaker['bio']) > 50 else speaker['bio']
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

if __name__ == "__main__":
    print("\nTED演讲者数据库展示\n" + "="*30)
    speakers = fetch_speakers()
    display_speakers(speakers)
