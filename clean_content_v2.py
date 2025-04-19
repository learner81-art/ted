import re
import sys
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.probability import FreqDist
from collections import defaultdict

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

def summarize_text(text):
    """生成最简洁中文摘要"""
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    
    sentences = sent_tokenize(text)
    if not sentences:
        return ""
        
    # 只保留包含中文且长度适中的句子
    chinese_sentences = [
        s.strip() for s in sentences 
        if any('\u4e00' <= char <= '\u9fff' for char in s)
        and len(s) < 100  # 限制句子长度
    ]
    
    if chinese_sentences:
        # 返回第一个符合条件的中文句子
        return chinese_sentences[0]
    
    return "未能提取有效摘要"

def clean_content(input_file, output_file, summary_file=None):
    # 定义更严格的清理模式
    color_pattern = re.compile(r'\[r=[^\]]+\]')  # 匹配所有颜色标记
    explanation_pattern = re.compile(r'\[:[^\]]+\]')  # 匹配所有单词解释
    special_chars = re.compile(r'[^\w\s\u4e00-\u9fa5，。、；：？！（）《》【】]')  # 保留中英文和常见标点
    
    full_text = []
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        f_sum = open(summary_file, 'w', encoding='utf-8') if summary_file else None
        
        for line in f_in:
            # 保留文件分段结构
            if line.startswith('==='):
                f_out.write(line)
                continue
                
            # 应用清理规则
            cleaned_line = color_pattern.sub('', line)  # 移除颜色标记
            cleaned_line = explanation_pattern.sub('', cleaned_line)  # 移除单词解释
            cleaned_line = special_chars.sub('', cleaned_line)  # 移除特殊字符
            
            # 处理英文单词分词
            if any(char.isalpha() for char in cleaned_line):  # 如果包含英文字母
                tokens = word_tokenize(cleaned_line)
                cleaned_line = ' '.join(tokens)
            
            # 写入清理后的行
            if cleaned_line.strip():  # 只写入非空行
                f_out.write(cleaned_line + '\n')
                full_text.append(cleaned_line)
    
    if summary_file:
        # 生成简洁摘要
        summary = summarize_text(' '.join(full_text))
        f_sum.write("=== 小结/Summary ===\n")
        f_sum.write(summary + '\n')

if __name__ == '__main__':
    if len(sys.argv) not in [3,4]:
        print("Usage: python clean_content_v2.py <input_file> <output_file> [summary_file]")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    summary_file = sys.argv[3] if len(sys.argv) > 3 else None
    clean_content(input_file, output_file, summary_file)
    print(f"Content cleaned and saved to {output_file}")
