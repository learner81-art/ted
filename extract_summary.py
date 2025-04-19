import re

def extract_section(text, lang):
    """处理单个语言部分的内容"""
    # 清理文本中的特殊标记和冗余信息
    text = re.sub(r'锡育软件第页共页', '', text)
    text = re.sub(r'迪斯尼美国动画影片制作家及制片人', '迪士尼', text)
    text = re.sub(r'[a-zA-Z]+n\s*', '', text)  # 去除英文单词标记
    
    # 提取核心段落
    paragraphs = text.split('\n')
    summary = []
    categories = {
        '演讲者': [],
        '核心观点': [],
        '关键数据': [],
        '行动建议': [],
        '重要引言': []
    }
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # 分类处理段落
        if '演讲者：' in para:
            categories['演讲者'].append(para)
        elif any(keyword in para for keyword in ['观点', '认为', '指出']):
            categories['核心观点'].append(para)
        elif any(keyword in para for keyword in ['数据', '统计', '调查']):
            categories['关键数据'].append(para)
        elif any(keyword in para for keyword in ['建议', '呼吁', '应该']):
            categories['行动建议'].append(para)
        elif len(para) > 100:  # 长段落作为重要引言
            categories['重要引言'].append(para)
    
    # 生成分类摘要
    result = []
    for category, items in categories.items():
        if items:
            result.append(f"### {category}")
            result.extend(items)
            result.append("")
    
    return "\n".join(result)

def extract_main_content(input_file, output_file):
    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取中英文内容部分
    sections = re.split(r'=== (中文|英文)内容 ===', content)[1:]
    chinese_content = sections[1] if len(sections) > 1 else ""
    english_content = sections[3] if len(sections) > 3 else ""
    
    # 处理各语言部分
    chinese_summary = extract_section(chinese_content, 'zh')
    english_summary = extract_section(english_content, 'en')
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=== 中文摘要 ===\n")
        f.write(chinese_summary)
        f.write("\n\n=== 英文摘要 ===\n")
        f.write(english_summary)
        f.write("\n")

if __name__ == "__main__":
    input_file = "AbigailDisney_2020_最终清理版.txt"
    output_file = "AbigailDisney_2020_摘要版.txt"
    extract_main_content(input_file, output_file)
    print(f"摘要已提取并保存到 {output_file}")
