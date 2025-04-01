import os
import sys
from single_pdf_parser import parse_single_pdf

def process_pdf_directory(directory):
    """
    处理目录中的所有PDF文件
    """
    results = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(directory, filename)
            result = parse_single_pdf(pdf_path)
            if result:
                results.append(result)
    return results

def generate_output(results):
    """
    生成输出字符串
    """
    output = ""
    for result in results:
        output += f"""
文件名: {result['filename']}
演讲者: {result['speaker']}
年份: {result['year']}
主题: {result['topic']}
总结: {result['summary']}
"""
        output += "\n" + "="*50 + "\n"  # 添加分隔线
    return output

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python batch_pdf_parser.py [PDF目录路径]")
        sys.exit(1)
    
    pdf_dir = sys.argv[1]
    if not os.path.isdir(pdf_dir):
        print(f"错误: {pdf_dir} 不是有效目录")
        sys.exit(1)
    
    results = process_pdf_directory(pdf_dir)
    if not results:
        print("没有找到可解析的PDF文件")
        sys.exit(1)
    
    # 打印结果到控制台
    output_str = generate_output(results)
    print(output_str)
    
    # 写入结果到文件
    with open("TED_analysis.txt", "a", encoding="utf-8") as f:
        f.write(output_str)
