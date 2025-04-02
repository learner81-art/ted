import mysql.connector
from faker import Faker
import random
import os
from datetime import datetime

# 初始化Faker
fake = Faker()

# 数据库连接配置
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'root',
    'database': 'ted_talks_db'
}

# 职业列表
professions = [
    '科学家', '工程师', '医生', '教师', '艺术家',
    '作家', '企业家', '心理学家', '社会活动家', '环保人士'
]

# 组织列表
organizations = [
    '哈佛大学', '斯坦福大学', '谷歌', '微软', '联合国',
    '世界卫生组织', '绿色和平', 'TED', 'MIT', 'NASA'
]

def parse_speakers_from_file(file_path):
    """从文本文件解析演讲者数据"""
    speakers = []
    year = str(datetime.now().year)  # 默认使用当前年份
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().split('\n\n')  # 按空行分割不同演讲者
    except Exception as e:
        print(f"读取文件错误: {e}")
        return speakers
        
    for entry in content:
        if not entry.strip():
            continue
            
        data = {}
        for line in entry.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                if key == '演讲者':
                    data['chinese_name'] = value
                elif key == '英文名':
                    data['english_name'] = value
                elif key == '主题':
                    data['bio'] = value
                elif key == '年份':
                    year = value.strip()  # 从文件内容获取年份
        
        if data:
            # 添加随机职业和组织
            data.update({
                'profession': random.choice(professions),
                'organization': random.choice(organizations),
                'photo_url': f"https://example.com/speakers/{data.get('english_name', '').lower()}.jpg",
                'year': year
            })
            speakers.append(data)
    
    return speakers

def insert_speakers(speakers):
    """向数据库插入演讲者数据"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO speakers 
        (english_name, chinese_name, profession, organization, bio, photo_url, year)
        VALUES (%(english_name)s, %(chinese_name)s, %(profession)s, 
                %(organization)s, %(bio)s, %(photo_url)s, %(year)s)
        """
        
        cursor.executemany(insert_query, speakers)
        conn.commit()
        print(f"成功插入 {cursor.rowcount} 条演讲者记录")
        
    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    # 获取用户输入的文件路径
    while True:
        file_path = input("请输入包含演讲者数据的文本文件路径(例如: ted_analysis_output - test.txt): ").strip()
        # 处理路径中的反斜杠和空格
        file_path = file_path.replace('\\', '/').strip('"\'')
        try:
            # 尝试打开文件验证路径是否正确
            with open(file_path, 'r', encoding='utf-8') as f:
                pass
            break
        except FileNotFoundError:
            print(f"错误: 文件 '{file_path}' 不存在，请检查路径后重新输入")
        except Exception as e:
            print(f"错误: 路径格式不正确，请使用正斜杠(/)分隔目录，或输入相对路径")
    
    # 从文件解析演讲者数据
    speakers_data = parse_speakers_from_file(file_path)
    # 插入数据库
    if speakers_data:
        insert_speakers(speakers_data)
    else:
        print("未解析到有效的演讲者数据")
