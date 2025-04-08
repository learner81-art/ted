# Docker环境数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',  # 从宿主机连接使用本地回环地址
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'ted_talks_db',
    'charset': 'utf8mb4'
}

def get_db_connection():
    """
    获取数据库连接(适配Docker环境)
    """
    import pymysql
    try:
        connection = pymysql.connect(**DB_CONFIG)
        print("成功连接到Docker中的MySQL数据库")
        return connection
    except pymysql.Error as e:
        print(f"数据库连接失败: {e}")
        raise

if __name__ == '__main__':
    # 测试连接
    conn = get_db_connection()
    conn.close()
