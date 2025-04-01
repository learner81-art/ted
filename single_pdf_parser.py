import re
import PyPDF2

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

def generate_summary(pdf_content):
    """
    从PDF内容生成简单摘要
    """
    text = pdf_content[:200].replace('\n', ' ')
    if len(text) == 200:
        text += "..."
    return text

def parse_single_pdf(pdf_path):
    """
    解析单个TED PDF文件
    返回结构化结果字典
    """
    filename = pdf_path.split('/')[-1]
    result = parse_ted_filename(filename)
    if not result:
        return None
    
    try:
        with open(pdf_path, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            pdf_content = ""
            for page in reader.pages:
                pdf_content += page.extract_text()
            
            summary = generate_summary(pdf_content)
    except Exception as e:
        summary = "待定"
    
    return {
        'filename': filename,
        'speaker': result['chinese_name'],
        'year': result['year'],
        'topic': result['content'],
        'summary': summary
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("用法: python single_pdf_parser.py [PDF文件路径]")
        sys.exit(1)
    
    result = parse_single_pdf(sys.argv[1])
    if not result:
        print("无法解析文件名格式")
        sys.exit(1)
    
    # 打印结果到控制台
    output_str = f"""
文件名: {result['filename']}
演讲者: {result['speaker']}
年份: {result['year']}
主题: {result['topic']}
总结: {result['summary']}
"""
    print(output_str)
    
    # 写入结果到文件
    with open("TED_analysis.txt", "a", encoding="utf-8") as f:
        f.write(output_str)
        f.write("\n" + "="*50 + "\n")  # 添加分隔线
