from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.text_rank import TextRankSummarizer
import jieba
import re
from pathlib import Path

def summarize_text(text, language="english", sentences_count=10):
    # 初始化摘要器
    if language == "english":
        summarizer = TextRankSummarizer()
    else:
        summarizer = LsaSummarizer()
    
    # 处理文本
    parser = PlaintextParser.from_string(text, Tokenizer(language))
    
    # 生成摘要
    summary = summarizer(parser.document, sentences_count)
    return " ".join([str(sentence) for sentence in summary])

def split_chinese_text(text):
    # 使用jieba进行中文分词
    return " ".join(jieba.cut(text))

def main():
    input_file = "AbigailDisney_2020_摘要版.txt"
    output_file = "AbigailDisney_2020_免费摘要版.txt"
    
    try:
        content = Path(input_file).read_text(encoding='utf-8')
        
        # 分割中英文内容
        zh_part = content.split("=== 中文摘要 ===")[1].split("=== 英文摘要 ===")[0]
        en_part = content.split("=== 英文摘要 ===")[1]
        
        # 预处理中文文本
        zh_processed = split_chinese_text(zh_part)
        
        print("正在处理中文摘要...")
        zh_summary = summarize_text(zh_processed, "chinese", 15)
        
        print("正在处理英文摘要...")
        en_summary = summarize_text(en_part, "english", 15)
        
        # 保存结果
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=== 中文精简摘要 ===\n")
            f.write(zh_summary + "\n\n")
            f.write("=== 英文精简摘要 ===\n")
            f.write(en_summary + "\n")
            
        print(f"摘要处理完成，结果已保存到 {output_file}")
        
    except Exception as e:
        print(f"处理过程中出错: {str(e)}")

if __name__ == "__main__":
    main()
