from kafka import KafkaConsumer, KafkaProducer
import json
import jieba
import langdetect
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import configparser
import logging
import mysql.connector
from mysql.connector import pooling

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载配置
config = configparser.ConfigParser()
config.read('nlpfilter_config.ini')

# 初始化数据库连接池
db_pool = pooling.MySQLConnectionPool(
    pool_name="nlp_pool",
    pool_size=int(config['database']['pool_size']),
    host=config['database']['host'],
    port=int(config['database']['port']),
    user=config['database']['username'],
    password=config['database']['password'],
    database=config['database']['name'],
    connection_timeout=int(config['database']['connection_timeout']),
    ssl_disabled=True
)

# 初始化Kafka消费者
consumer = KafkaConsumer(
    config['kafka']['topic_raw'],
    bootstrap_servers=config['kafka']['bootstrap_servers'].split(','),
    group_id=config['kafka']['consumer_group'],
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# 初始化Kafka生产者
producer = KafkaProducer(
    bootstrap_servers=config['kafka']['bootstrap_servers'].split(','),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def process_text(text):
    """处理文本内容，过滤无意义词句"""
    try:
        # 检测语言
        lang = langdetect.detect(text)
        
        # 根据语言进行分词处理
        if lang == 'zh':
            words = jieba.lcut(text)
            # 中文停用词过滤
            stop_words = set(['的', '了', '在', '是', '我', '有', '和', '就', '不', '人'])
        else:
            words = word_tokenize(text)
            # 英文停用词过滤
            stop_words = set(stopwords.words('english'))
        
        # 过滤停用词和短词
        filtered_words = [
            word for word in words 
            if word not in stop_words and len(word) > 1
        ]
        
        return ' '.join(filtered_words)
    
    except Exception as e:
        logger.error(f"文本处理失败: {e}")
        return text

def save_to_database(task_id, original_text, processed_text, stats):
    """保存处理结果到数据库"""
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor()
        
        # 保存原始文本
        cursor.execute(
            "INSERT INTO raw_texts (task_id, original_content, content_hash) VALUES (%s, %s, MD5(%s))",
            (task_id, original_text, original_text)
        )
        text_id = cursor.lastrowid
        
        # 保存处理结果
        cursor.execute(
            "INSERT INTO filtered_results (text_id, processed_content, filter_stats) VALUES (%s, %s, %s)",
            (text_id, processed_text, json.dumps(stats))
        )
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"数据库保存失败: {e}")
        return False
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def process_message(msg):
    """处理Kafka消息"""
    try:
        data = msg.value
        if 'content' not in data:
            logger.warning("消息缺少content字段")
            return None
            
        # 处理文本内容
        processed_content = process_text(data['content'])
        
        # 构建结果消息
        result = {
            'original_id': data.get('id', ''),
            'processed_content': processed_content,
            'timestamp': data.get('timestamp', ''),
            'metadata': data.get('metadata', {}),
            'task_id': data.get('task_id', 0)
        }
        
        # 保存到数据库
        stats = {
            'length_before': len(data['content']),
            'length_after': len(processed_content),
            'language': langdetect.detect(data['content'])
        }
        save_to_database(
            result['task_id'],
            data['content'],
            processed_content,
            stats
        )
        
        return result
        
    except Exception as e:
        logger.error(f"消息处理失败: {e}")
        return None

def consume_messages():
    """消费并处理消息"""
    logger.info("启动Kafka消费者...")
    for msg in consumer:
        result = process_message(msg)
        if result:
            try:
                # 发送处理后的消息
                producer.send(
                    config['kafka']['topic_clean'],
                    value=result
                )
                logger.info(f"处理完成: {result['original_id']}")
            except Exception as e:
                logger.error(f"发送处理结果失败: {e}")

if __name__ == "__main__":
    consume_messages()
