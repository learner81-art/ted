import os
import re
import mysql.connector
import configparser
import logging
import datetime
from typing import List, Dict

# 初始化基础日志系统（确保最早可用）
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()],
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 读取配置文件（带编码处理）
config = configparser.ConfigParser()
try:
    with open('config.ini', 'r', encoding='utf-8') as f:
        config.read_file(f)
except UnicodeDecodeError:
    try:
        with open('config.ini', 'r', encoding='gbk') as f:
            config.read_file(f)
    except Exception as e:
        logger.error(f"无法读取配置文件: {e}")
        raise

# 配置完整日志系统
try:
    log_dir = config.get('logging', 'log_dir', fallback='logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"update_pdf_url_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # 添加文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S'))
    logger.addHandler(file_handler)
    
    logger.info(f"日志系统初始化完成，日志文件: {log_file}")
except Exception as e:
    logger.error(f"初始化日志文件失败: {e}")
    log_file = f"update_pdf_url_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logger.info(f"使用当前目录作为日志文件: {log_file}")

# 检查配置文件必要字段
required_sections = ['database']
for section in required_sections:
    if not config.has_section(section):
        logger.error(f"配置文件中缺少必要部分: [{section}]")
        raise ValueError(f"配置文件中缺少必要部分: [{section}]")

logger.info("配置文件检查完成")

# 数据库连接配置 - 从配置文件读取
db_config = {
    'host': config.get('database', 'host', fallback='localhost'),
    'user': config.get('database', 'user', fallback='root'),
    'password': config.get('database', 'password', fallback='root'),
    'database': config.get('database', 'database', fallback='ted_talks_db')
}

def parse_analysis_file(filepath: str) -> List[Dict]:
    """解析分析文件获取PDF信息，只处理包含'文件名'的行"""
    try:
        # 尝试多种编码方式读取文件
        encodings = ['utf-8', 'gbk', 'gb18030', 'big5']
        content = None
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read().splitlines()
                    break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            raise ValueError(f"无法用任何支持的编码({', '.join(encodings)})读取文件")
        
        records = []
        for line in content:
            line = line.strip()
            if not line or '文件名:' not in line:
                continue
                
            # 解析包含"文件名"的行
            try:
                # 匹配格式如"1. 文件名: 1. 123.pdf"
                match = re.match(r'(\d+)\.\s+文件名:\s+\d+\.\s+([^\s]+\.pdf)', line)
                if match:
                    file_id = int(match.group(1))
                    filename = match.group(2)
                    records.append({
                        'id': file_id,
                        'filename': filename,
                        'chinese_name': '',
                        'english_name': '',
                        'year': '',
                        'topic': ''
                    })
            except Exception as e:
                logger.warning(f"解析行失败: {line}, 错误: {e}")
            
        return records
    except Exception as e:
        logger.error(f"解析文件错误: {e}")
        return []

def update_database(pdf_info: Dict) -> int:
    """更新数据库中的pdf_url字段"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        update_query = """
        UPDATE `ted_talks_db`.`speakers` 
        SET `pdf_url` = %s
        WHERE `id` = %s
        """
        
        base_url = config.get('pdf', 'base_url', fallback='http://ted.source.com')
        pdf_url = f"{base_url}/{pdf_info['filename']}"
        params = (pdf_url, pdf_info['id'])
        
        logger.info(f"准备更新ID {pdf_info['id']} 的PDF URL为: {pdf_url}")
        cursor.execute(update_query, params)
        conn.commit()
        
        return cursor.rowcount
        
    except mysql.connector.Error as err:
        logger.error(f"数据库错误: {err}")
        return 0
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def get_input_file() -> str:
    """获取用户输入的分析文件路径"""
    default_path = config.get('paths', 'input_path', fallback='')
    while True:
        filepath = input(f"请输入分析文件路径(默认: {default_path}): ").strip() or default_path
        if os.path.exists(filepath):
            return filepath
        logger.error(f"文件 '{filepath}' 不存在，请重新输入")

def main():
    logger.info("开始批量更新PDF URL")
    
    filepath = get_input_file()
    records = parse_analysis_file(filepath)
    
    if not records:
        logger.warning("没有找到有效记录")
        return
        
    logger.info(f"找到 {len(records)} 条记录待处理")
    total_updated = 0
    
    for record in records:
        updated = update_database(record)
        total_updated += updated
        logger.info(f"处理记录ID {record['id']}: {record['filename']}, 更新了 {updated} 条记录")
            
    logger.info(f"处理完成，总共更新了 {total_updated} 条记录的pdf_url")

if __name__ == "__main__":
    main()
