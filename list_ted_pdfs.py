import os
import re

def parse_ted_filename(filename):
    """
    解析TED文件名格式：英文名_年份[中文名][文章内容].pdf
    返回包含英文名、年份、中文名和文章内容的字典
    """
    pattern = r'^(.*?)_(\d{4})(?:[A-Z])?\[(.*?)\]\[(.*?)\]\.pdf$|^(.*?)_(\d{4})X\[(.*?)\]\[(.*?)\]\.pdf$'
    match = re.match(pattern, filename)
    if not match:
        return None
    
    if match.lastindex == 4:  # 匹配第一种格式
        return {
            'english_name': match.group(1),
            'year': match.group(2),
            'chinese_name': match.group(3),
            'content': match.group(4)
        }
    elif match.lastindex == 8:  # 匹配第二种格式
        return {
            'english_name': match.group(5),
            'year': match.group(6),
            'chinese_name': match.group(7),
            'content': match.group(8)
        }

def list_ted_pdfs(directory):
    """
    遍历目录中的TED PDF文件并格式化输出信息
    """
    if not os.path.isdir(directory):
        print(f"错误: {directory} 不是有效目录")
        return
    
    count = 1
    for filename in os.listdir(directory):
        if filename.lower().endswith('.pdf'):
            result = parse_ted_filename(filename)
            if result:
                print(f"{count}. 文件名: {filename}")
                print(f"   演讲者: {result['chinese_name']}")
                print(f"   年份: {result['year']}")
                print(f"   主题: {result['content']}\n")
                count += 1
            else:
                print(f"警告: 无法解析文件名格式: {filename}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("用法: python list_ted_pdfs.py [PDF目录路径]")
        sys.exit(1)
    
    pdf_dir = sys.argv[1]
    if not os.path.isdir(pdf_dir):
        print(f"错误: {pdf_dir} 不是有效目录")
        sys.exit(1)
    
    list_ted_pdfs(pdf_dir)
