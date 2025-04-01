import os
import re

def parse_ted_line(line):
    """
    解析TED文本行格式：英文名_年份[中文名][文章内容].pdf
    返回包含英文名、年份、中文名和文章内容的字典
    """
    pattern = r'^(.*?)_(\d{4})(?:[A-Z])?\[(.*?)\]\[(.*?)\]\.pdf$|^(.*?)_(\d{4})X\[(.*?)\]\[(.*?)\]\.pdf$'
    match = re.match(pattern, line.strip())
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

def process_text_file(input_file, output_file):
    """
    处理输入文本文件并生成格式化输出
    """
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        
        count = 1
        for line in infile:
            if line.strip():  # 跳过空行
                result = parse_ted_line(line)
                if result:
                    outfile.write(f"{count}. 文件名: {line.strip()}\n")
                    # 过滤英文名中的数字和点
                    english_name = re.sub(r'[\d.]', '', result['english_name'])
                    outfile.write(f"   演讲者: {result['chinese_name']}\n")
                    outfile.write(f"   英文名: {english_name}\n")
                    outfile.write(f"   年份: {result['year']}\n") 
                    outfile.write(f"   主题: {result['content']}\n\n")
                    count += 1

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("用法: python text_parser.py [输入文件] [输出文件]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.isfile(input_file):
        print(f"错误: {input_file} 不是有效文件")
        sys.exit(1)
        
    process_text_file(input_file, output_file)
    print(f"处理完成，结果已保存到 {output_file}")
