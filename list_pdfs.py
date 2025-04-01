import os
import re

def parse_pdf_info(filename):
    """从PDF文件名中解析年份、演讲者和内容"""
    # 匹配格式: 演讲者_年份[中文名][内容]
    pattern = r'^([\w\s-]+)_(\d{4})\[([^\]]+)\]\[([^\]]+)\]\.pdf$'
    match = re.match(pattern, filename, re.IGNORECASE)
    if match:
        return {
            'speaker_en': match.group(1),
            'year': match.group(2),
            'speaker_cn': match.group(3),
            'content': match.group(4)
        }
    return None

def list_pdfs(directory, output_file):
    """列出指定目录下所有PDF文件并解析信息保存到输出文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        count = 1
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.pdf'):
                    info = parse_pdf_info(file)
                    f.write(f"{count}. {file}\n")
                    if info:
                        f.write(f"   年份: {info['year']}\n")
                        f.write(f"   演讲者(英文): {info['speaker_en']}\n")
                        f.write(f"   演讲者(中文): {info['speaker_cn']}\n")
                        f.write(f"   内容: {info['content']}\n")
                    f.write("\n")
                    print(f"Found PDF [{count}]: {file}")
                    count += 1
    
    print(f"\nAll PDF files have been listed and parsed in {output_file}")

if __name__ == "__main__":
    import argparse
    
    # 默认扫描当前脚本所在目录
    default_dir = os.path.dirname(__file__)
    default_output = os.path.join(default_dir, 'pdf_list.txt')
    
    parser = argparse.ArgumentParser(description='List all PDF files in a directory')
    parser.add_argument('directory', nargs='?', default=default_dir,
                      help='Directory to scan for PDF files (default: script directory)')
    parser.add_argument('-o', '--output', help='Output file path', 
                       default=default_output)
    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        print(f"Error: Directory not found - {args.directory}")
        exit(1)
        
    print(f"Scanning for PDF files in: {args.directory}")
    print(f"Output will be saved to: {args.output}")
    list_pdfs(args.directory, args.output)
