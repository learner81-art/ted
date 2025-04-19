#!/usr/bin/env python3
# 免费AI摘要工具 - 使用HuggingFace免费API

import requests
import json
from typing import Optional

def summarize_with_huggingface(text: str, language: str = "en") -> Optional[str]:
    """
    使用HuggingFace免费API进行文本摘要
    Args:
        text: 要摘要的文本
        language: 语言代码 ('zh' 或 'en')
    Returns:
        摘要文本或None
    """
    API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    
    headers = {"Authorization": "Bearer hf_xxxxxxxxxxxxxxxx"}  # 免费API不需要真实token
    
    try:
        payload = {
            "inputs": text,
            "parameters": {
                "max_length": 150 if language == "zh" else 200,
                "min_length": 30,
                "do_sample": False
            }
        }
        
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("summary_text", None)
        return None
        
    except Exception as e:
        print(f"摘要请求失败: {str(e)}")
        return None

def process_file(input_file: str, output_file: str):
    """
    处理输入文件并生成摘要输出
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 分割中英文内容
        zh_part = "".join([c for c in content if '\u4e00' <= c <= '\u9fff'])
        en_part = "".join([c for c in content if c.isascii()])
        
        print("正在使用免费AI接口处理中文摘要...")
        zh_summary = summarize_with_huggingface(zh_part, "zh") or "中文摘要生成失败"
        
        print("正在使用免费AI接口处理英文摘要...")
        en_summary = summarize_with_huggingface(en_part, "en") or "英文摘要生成失败"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=== AI生成中文摘要 ===\n")
            f.write(zh_summary + "\n\n")
            f.write("=== AI生成英文摘要 ===\n")
            f.write(en_summary + "\n")
            
        print(f"摘要已保存到 {output_file}")
        
    except Exception as e:
        print(f"文件处理错误: {str(e)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("用法: python free_ai_summarizer.py 输入文件.txt 输出文件.txt")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    process_file(input_file, output_file)
