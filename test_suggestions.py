#!/usr/bin/env python3
import requests
import json
from pprint import pprint

# Elasticsearch配置
ES_HOST = 'http://localhost:9200'
ES_INDEX = 'ted_talks'

def es_ping():
    """检查Elasticsearch连接"""
    try:
        resp = requests.get(ES_HOST, timeout=5)
        return resp.status_code == 200
    except:
        return False

def get_suggestions(title_query="", eng_query="", ch_query="", use_term_suggest=False):
    """查询Elasticsearch获取建议
    Args:
        title_query: 标题关键词
        eng_query: 英文名关键词
        ch_query: 中文名关键词
        use_term_suggest: 是否使用分词建议(默认为False使用普通搜索)
    """
    if not any([title_query, eng_query, ch_query]):
        return []
    
    try:
        if use_term_suggest:
            # 使用多字段模糊匹配搜索替代分词建议
            es_query = {
                "query": {
                    "multi_match": {
                        "query": title_query or eng_query or ch_query,
                        "fields": [
                            "metadata.content^3.5",
                            "metadata.english_name^2.0", 
                            "metadata.chinese_name^1.8"
                        ],
                        "fuzziness": "AUTO",
                        "operator": "or",
                        "analyzer": "english",  # 使用英文分析器处理英文内容
                        "auto_generate_synonyms_phrase_query": True,
                        "lenient": True  # 允许格式错误
                    }
                },
                "size": 10
            }
            
            resp = requests.post(
                f"{ES_HOST}/{ES_INDEX}/_search",
                json=es_query,
                timeout=5
            )
            resp.raise_for_status()
            
            # 提取结果
            suggestions = []
            for hit in resp.json().get('hits', {}).get('hits', []):
                source = hit['_source']
                suggestions.append({
                    'term': source.get('metadata', {}).get('content', '') or 
                           source.get('metadata', {}).get('english_name', '') or 
                           source.get('metadata', {}).get('chinese_name', ''),
                    'score': hit['_score']
                })
            return suggestions[:10]
            
        else:
            # 原始的多字段加权查询
            es_query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "english_content": {
                                    "query": title_query,
                                    "boost": 3.5,
                                    "fuzziness": "AUTO",
                                    "analyzer": "english",
                                    "lenient": True
                                }
                            }
                        } if title_query else None,
                        {
                            "match": {
                                "metadata.english_name": {
                                    "query": eng_query,
                                    "boost": 2.0,
                                    "fuzziness": 1,
                                    "analyzer": "english",
                                    "lenient": True
                                }
                            }
                        } if eng_query else None,
                        {
                            "match": {
                                "metadata.chinese_name": {
                                    "query": ch_query,
                                    "boost": 1.8,
                                    "fuzziness": 1
                                }
                            }
                        } if ch_query else None
                    ],
                    "minimum_should_match": 1
                }
            },
            "size": 10,
            "_source": ["english_content", "metadata.english_name", "metadata.chinese_name"]
        }
        
        # 移除None值
        es_query['query']['bool']['should'] = [x for x in es_query['query']['bool']['should'] if x is not None]
        
        resp = requests.post(
            f"{ES_HOST}/{ES_INDEX}/_search",
            json=es_query,
            timeout=5
        )
        resp.raise_for_status()
        
        # 提取建议并按权重排序
        suggestions = []
        for hit in resp.json().get('hits', {}).get('hits', []):
            source = hit['_source']
            suggestions.append({
                'term': source.get('metadata', {}).get('content', '') or 
                       source.get('metadata', {}).get('english_name', '') or 
                       source.get('metadata', {}).get('chinese_name', ''),
                'score': hit['_score']
            })
        
        # 按分数降序排序
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions[:10]
        
    except Exception as e:
        print(f"搜索建议查询失败: {e}")
        return []

def test_suggestion(title_query="", eng_query="", ch_query="", expected_type="", use_term_suggest=False):
    """测试ES建议功能
    Args:
        title_query: 标题关键词
        eng_query: 英文名关键词
        ch_query: 中文名关键词
        expected_type: 测试类型描述
        use_term_suggest: 是否测试分词建议
    """
    print(f"\n=== 测试 [{expected_type}] ===")
    print(f"标题关键词: '{title_query}'")
    print(f"英文名关键词: '{eng_query}'")
    print(f"中文名关键词: '{ch_query}'")
    if use_term_suggest:
        print("🔍 使用分词建议模式")
    
    if not es_ping():
        print("❌ Elasticsearch连接失败")
        return False
    
    suggestions = get_suggestions(title_query, eng_query, ch_query, use_term_suggest)
    
    if not suggestions:
        print("⚠️ 未返回任何建议")
        return False
        
    print("\nTop 10 分词建议:")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion['term']} (score: {suggestion['score']:.2f})")
    
    # 验证权重排序
    if len(suggestions) > 1:
        prev_score = suggestions[0]['score']
        for i in range(1, len(suggestions)):
            if suggestions[i]['score'] > prev_score:
                print(f"⚠️ 权重排序错误: 第{i}条得分{suggestions[i]['score']:.2f}高于第{i-1}条{prev_score:.2f}")
                return False
            prev_score = suggestions[i]['score']
        print("✅ 权重排序正确")
    return True

if __name__ == "__main__":
    # 定义测试用例
    test_cases = [
        {"title_query": "", "eng_query": "Bill", "ch_query": "", "type": "英文姓名"},
        {"title_query": "", "eng_query": "", "ch_query": "李", "type": "中文姓名"},
        {"title_query": "未来", "eng_query": "", "ch_query": "", "type": "演讲标题"},
        {"title_query": "tech", "eng_query": "", "ch_query": "", "type": "英文标题"},
        {"title_query": "tECH", "eng_query": "", "ch_query": "", "type": "大小写测试"},
        {"title_query": "teh", "eng_query": "", "ch_query": "", "type": "模糊匹配测试"},
        {"title_query": "科技", "eng_query": "AI", "ch_query": "人工智能", "type": "混合搜索"},
        {"title_query": "未来", "eng_query": "Elon", "ch_query": "", "type": "高权重标题测试"},
        {"title_query": "", "eng_query": "Jobs", "ch_query": "乔布斯", "type": "姓名权重测试"}
    ]

    # 分词建议专用测试用例
    term_suggest_cases = [
        {"title_query": "未来科技", "type": "中文分词建议"},
        {"title_query": "artificial intelligence", "type": "英文分词建议"},
        {"title_query": "AI技术", "type": "混合分词建议"}
    ]
    
    print("=== 开始测试 Elasticsearch 搜索建议功能 ===")
    print(f"ES地址: {ES_HOST}")
    print(f"索引: {ES_INDEX}")
    
    # 执行普通搜索测试
    results = {}
    for case in test_cases:
        results[f"{case['type']}"] = test_suggestion(
            case['title_query'],
            case['eng_query'],
            case['ch_query'],
            case['type']
        )
    
    # 执行分词建议测试
    term_results = {}
    for case in term_suggest_cases:
        term_results[f"{case['type']}"] = test_suggestion(
            case['title_query'],
            "",
            "",
            case['type'],
            use_term_suggest=True
        )
    
    # 汇总结果
    print("\n=== 普通搜索测试汇总 ===")
    for query, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {query}")
    
    print("\n=== 分词建议测试汇总 ===")
    for query, passed in term_results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {query}")
    
    print("\n测试完成")
