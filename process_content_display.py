import sqlite3
import re
from zhconv import convert

def process_content(content):
    # 繁体转简体
    content = convert(content, 'zh-cn')
    
    # 分割中英文段落
    paragraphs = content.split('\n\n')
    processed = []
    
    for para in paragraphs:
        # 去除多余空格和换行
        para = re.sub(r'\s+', ' ', para.strip())
        
        # 分割中英文句子
        sentences = re.split(r'([\u4e00-\u9fff]+)', para)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 配对中英文
        for i in range(0, len(sentences), 2):
            if i+1 < len(sentences):
                processed.append(f"{sentences[i]}\n{sentences[i+1]}")
            else:
                processed.append(sentences[i])
    
    return '\n\n'.join(processed)

def main():
    # 连接数据库
    conn = sqlite3.connect('ted_talks.db')
    cursor = conn.cursor()
    
    # 检查并添加content_display列
    cursor.execute("PRAGMA table_info(talks)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'content_display' not in columns:
        cursor.execute("ALTER TABLE talks ADD COLUMN content_display TEXT")
    
    # 获取所有需要处理的记录
    cursor.execute("SELECT id, content FROM talks WHERE content_display IS NULL")
    records = cursor.fetchall()
    
    # 处理每条记录
    for id, content in records:
        if content:
            processed = process_content(content)
            cursor.execute("UPDATE talks SET content_display=? WHERE id=?", 
                         (processed, id))
    
    conn.commit()
    conn.close()
    print(f"成功处理 {len(records)} 条记录")

if __name__ == '__main__':
    main()
