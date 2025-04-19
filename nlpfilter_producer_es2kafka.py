from kafka import KafkaProducer
from elasticsearch import Elasticsearch
import json
import configparser
from time import sleep

# 加载配置
config = configparser.ConfigParser()
config.read('nlpfilter_config.ini')

# 初始化Kafka生产者
producer = KafkaProducer(
    bootstrap_servers=config['kafka']['bootstrap_servers'].split(','),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# 初始化ES连接
es = Elasticsearch(
    [f"{config['elasticsearch']['host']}:{config['elasticsearch']['port']}"],
    http_auth=(
        config['elasticsearch']['username'],
        config['elasticsearch']['password']
    ) if config['elasticsearch']['username'] else None
)

def scroll_docs():
    """使用scroll API从ES批量获取文档并发送到Kafka"""
    body = {"query": {"match_all": {}}}
    res = es.search(
        index=config['elasticsearch']['index'],
        scroll='2m',
        size=int(config['processing']['chunk_size']),
        body=body
    )
    
    while res['hits']['hits']:
        for doc in res['hits']['hits']:
            try:
                # 发送到Kafka
                producer.send(
                    config['kafka']['topic_raw'],
                    value=doc['_source']
                )
            except Exception as e:
                print(f"发送消息到Kafka失败: {e}")
        
        res = es.scroll(
            scroll_id=res['_scroll_id'],
            scroll='2m'
        )
        sleep(0.1)  # 避免过载

if __name__ == "__main__":
    print("启动ES到Kafka的生产者...")
    scroll_docs()
    producer.flush()
    print("数据发送完成")
