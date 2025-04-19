import pika
from elasticsearch import Elasticsearch
import json
import configparser
from time import sleep

# 加载配置
config = configparser.ConfigParser()
config.read('nlpfilter_config.ini')

# 初始化RabbitMQ连接
connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=config['rabbitmq']['host'],
        port=int(config['rabbitmq']['port']),
        credentials=pika.PlainCredentials(
            config['rabbitmq']['username'],
            config['rabbitmq']['password']
        ) if config['rabbitmq']['username'] else None
    )
)
channel = connection.channel()
channel.queue_declare(queue=config['rabbitmq']['queue_raw'])

# 初始化ES连接
es = Elasticsearch(["http://localhost:9200"])

def scroll_docs():
    """使用scroll API从ES批量获取文档并发送到RabbitMQ"""
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
                # 发送到RabbitMQ
                channel.basic_publish(
                    exchange='',
                    routing_key=config['rabbitmq']['queue_raw'],
                    body=json.dumps(doc['_source'])
                )
            except Exception as e:
                print(f"发送消息到RabbitMQ失败: {e}")
        
        res = es.scroll(
            scroll_id=res['_scroll_id'],
            scroll='2m'
        )
        sleep(0.1)  # 避免过载

if __name__ == "__main__":
    print("启动ES到RabbitMQ的生产者...")
    scroll_docs()
    connection.close()
    print("数据发送完成")
