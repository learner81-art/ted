import requests
from datetime import datetime

# Elasticsearch基础URL
es_url = "http://localhost:9200"
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# 创建索引
index_name = "test_data"
try:
    # 检查索引是否存在
    resp = requests.get(f"{es_url}/{index_name}", headers=headers)
    if resp.status_code == 404:
        # 创建索引
        settings = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        }
        resp = requests.put(
            f"{es_url}/{index_name}",
            json=settings,
            headers=headers
        )
        resp.raise_for_status()
except Exception as e:
    print(f"创建索引时出错: {e}")

# 测试数据
test_data = [
    {
        "title": "Elasticsearch 测试文档 1",
        "content": "这是一个测试Elasticsearch的文档内容",
        "timestamp": datetime.now().isoformat(),
        "views": 100
    },
    {
        "title": "Elasticsearch 测试文档 2", 
        "content": "第二个测试文档，包含更多内容",
        "timestamp": datetime.now().isoformat(),
        "views": 50
    },
    {
        "title": "Python与Elasticsearch",
        "content": "如何使用Python客户端操作Elasticsearch",
        "timestamp": datetime.now().isoformat(),
        "views": 200
    }
]

# 批量插入数据
try:
    for i, doc in enumerate(test_data, 1):
        resp = requests.post(
            f"{es_url}/{index_name}/_doc/{i}",
            json=doc,
            headers=headers
        )
        resp.raise_for_status()
    print(f"成功插入 {len(test_data)} 条测试数据到 {index_name} 索引")
except Exception as e:
    print(f"插入数据时出错: {e}")
