import pymysql
from docker_db_config import DB_CONFIG
import logging
import time
import subprocess

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='/Users/a/Desktop/data/ted/db_test.log'
)

def test_connection(config, mode_name, max_retries=3):
    retry_count = 0
    while retry_count < max_retries:
        try:
            conn = pymysql.connect(**config)
            cursor = conn.cursor()
            
            # 检查数据库是否存在
            cursor.execute("SHOW DATABASES LIKE 'ted_talks_db'")
            if not cursor.fetchone():
                logging.error(f"{mode_name}模式: 数据库ted_talks_db不存在")
                return False
                
            # 测试基本查询
            cursor.execute("USE ted_talks_db")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            logging.info(f"{mode_name}模式: 数据库表列表: {tables}")
            
            # 测试计数查询
            cursor.execute("SELECT COUNT(*) FROM speakers")
            count = cursor.fetchone()[0]
            logging.info(f"{mode_name}模式: speakers表记录数: {count}")
            
            # 测试分页查询
            cursor.execute("SELECT id, name FROM speakers LIMIT 5")
            speakers = cursor.fetchall()
            logging.info(f"{mode_name}模式: 前5位演讲者: {speakers}")
            
            cursor.close()
            conn.close()
            return True
            
        except pymysql.Error as e:
            retry_count += 1
            wait_time = 2 * retry_count
            logging.warning(f"{mode_name}模式连接失败(尝试 {retry_count}/{max_retries}): {str(e)} - {wait_time}秒后重试")
            if retry_count < max_retries:
                time.sleep(wait_time)
        except Exception as e:
            logging.error(f"{mode_name}模式发生未知错误: {str(e)}")
            return False
    
    logging.error(f"{mode_name}模式: 达到最大重试次数({max_retries})仍连接失败")
    return False

def test_container_connection():
    print("正在测试容器连接...")
    try:
        # 获取当前运行的MySQL容器ID
        cmd = "docker ps --filter 'name=mysql' --format '{{.ID}}'"
        container_id = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True).stdout.strip()
        
        if not container_id:
            logging.error("未找到运行的MySQL容器")
            return False
            
        # 简单测试连接
        cmd = f"docker exec -i {container_id} mysql -u {DB_CONFIG['user']} -p{DB_CONFIG['password']} -e 'SELECT 1'"
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        
        if "ERROR" in result.stderr:
            logging.error(f"连接测试失败: {result.stderr}")
            return False
            
        logging.info(f"容器内连接成功 (容器ID: {container_id})")
        print(f"容器内连接成功 (容器ID: {container_id})")
        return True
        
    except subprocess.CalledProcessError as e:
        logging.error(f"命令执行失败: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"连接测试发生错误: {str(e)}")
        print(f"连接测试发生错误: {str(e)}")
        return False

def query_table_data(table_name, limit=5):
    print(f"\n正在查询表{table_name}数据...")
    try:
        # 获取容器IP
        cmd = "docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -qf 'name=mysql')"
        container_ip = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True).stdout.strip()
        
        if not container_ip:
            logging.error("无法获取容器IP地址")
            print("错误: 无法获取容器IP地址")
            return None, None
            
        container_config = {
            'host': container_ip,
            'port': 3306,
            'user': DB_CONFIG['user'],
            'password': DB_CONFIG['password'],
            'charset': 'utf8mb4'
        }
        
        # 先检查数据库是否存在
        conn = pymysql.connect(**container_config)
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES LIKE 'ted_talks_db'")
        if not cursor.fetchone():
            logging.error("数据库ted_talks_db不存在")
            print("错误: 数据库ted_talks_db不存在")
            cursor.close()
            conn.close()
            return None, None
            
        # 检查表是否存在
        cursor.execute("USE ted_talks_db")
        cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
        if not cursor.fetchone():
            logging.error(f"表{table_name}不存在")
            print(f"错误: 表{table_name}不存在")
            cursor.close()
            conn.close()
            return None, None
            
        # 查询表数据
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        data = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        cursor.close()
        conn.close()
        print(f"成功查询到{table_name}表数据")
        return columns, data
        
    except subprocess.CalledProcessError as e:
        logging.error(f"获取容器IP失败: {e.stderr}")
        return None, None
    except pymysql.Error as e:
        logging.error(f"数据库操作失败: {str(e)}")
        return None, None
    except Exception as e:
        logging.error(f"查询数据发生错误: {str(e)}")
        return None, None

if __name__ == "__main__":
    print("测试容器内数据库连接...")
    container_success = test_container_connection()
    
    if container_success:
        print("\n查询容器内数据:")
        tables = ["speakers", "talk_speakers", "talks", "ted_bak"]  # 实际表名
        for table in tables:
            columns, data = query_table_data(table)
            if columns and data:
                print(f"\n{table}表前5条数据:")
                print(columns)
                for row in data:
                    print(row)
            else:
                print(f"\n{table}表查询失败或不存在")
