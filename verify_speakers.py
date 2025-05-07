import mysql.connector

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'root',
    'database': 'ted_talks_db'
}

def verify_speakers():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, english_name, chinese_name, profession FROM speakers LIMIT 5")
        results = cursor.fetchall()
        
        with open('speakers_output.txt', 'w', encoding='utf-8') as f:
            f.write("前5条演讲者记录:\n")
            f.write("-" * 50 + "\n")
            for row in results:
                f.write(f"ID: {row[0]}, 英文名: {row[1]}, 中文名: {row[2]}, 职业: {row[3]}\n")
            f.write("-" * 50 + "\n")
        
    except Exception as err:
        with open('speakers_error.txt', 'w', encoding='utf-8') as f:
            f.write(f"执行错误: {str(err)}\n")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    verify_speakers()
#1234566