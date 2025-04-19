from elasticsearch import Elasticsearch
import json


def get_es_data(size=10):
    """从Elasticsearch获取指定数量的TED演讲数据"""
    es_url = "http://localhost:9200"
    index_name = "ted_talks"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        # 构建查询请求
        query = {
            "query": {
                "match_all": {}
            },
            "size": size,
            "sort": [
                {
                    "timestamp": {
                        "order": "desc"
                    }
                }
            ]
        }

        # 发送查询请求
        resp = requests.get(
            f"{es_url}/{index_name}/_search",
            headers=headers,
            data=json.dumps(query)
        )
        resp.raise_for_status()

        # 解析结果
        results = []
        data = resp.json()
        for hit in data.get('hits', {}).get('hits', []):
            source = hit['_source']
            results.append({
                'id': hit['_id'],
                'english_name': source.get('metadata', {}).get('english_name', ''),
                'chinese_name': source.get('metadata', {}).get('chinese_name', ''),
                'year': source.get('metadata', {}).get('year', ''),
                'timestamp': source.get('timestamp', ''),
                'content_length': len(source.get('chinese_content', '')) + len(source.get('english_content', ''))
            })

        return results

    except Exception as e:
        print(f"查询Elasticsearch时出错: {e}")
        return []

def print_results(results):
    """格式化打印查询结果"""
    print(f"\n获取到 {len(results)} 条TED演讲数据:\n")
    print("{:<40} {:<30} {:<8} {:<25} {:<10}".format(
        "ID", "英文标题", "年份", "时间戳", "内容长度"
    ))
    print("-" * 120)
    
    for item in results:
        print("{:<40} {:<30} {:<8} {:<25} {:<10}".format(
            item['id'][:37] + "..." if len(item['id']) > 40 else item['id'],
            item['english_name'][:27] + "..." if len(item['english_name']) > 30 else item['english_name'],
            item['year'],
            datetime.fromisoformat(item['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
            item['content_length']
        ))

if __name__ == "__main__":
    print("正在从Elasticsearch获取TED演讲数据...")
    results = get_es_data(10)
    print_results(results)
