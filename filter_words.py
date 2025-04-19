#!/usr/bin/env python3
import sys
import re
import pdfplumber
import tempfile
import requests
import os
from collections import defaultdict

def is_chinese(char):
    """检查字符是否为中文"""
    return '\u4e00' <= char <= '\u9fff'

# 严格匹配词典格式行：
# 基本格式：单词:释义
# 支持多释义(分号分隔)和多单词组合(空格分隔)
# 允许释义中包含括号、标点和空格
WORD_DEF_PATTERN = re.compile(r'^([a-zA-Z-]+:[^:]+(;|,)[^:]+(;|,)*[^:]*)(\s+[a-zA-Z-]+:[^:]+(;|,)[^:]+(;|,)*[^:]*)*[;,]?\s*$|^[a-zA-Z-]+:[^:]+(;|,)[^:]+(;|,)*[^:]*\s*$')

def remove_color_tags(text):
    """移除颜色标记并合并英文单词"""
    # 移除所有<color>标签
    text = re.sub(r'<color[^>]*>', '', text)
    text = text.replace('</color>', '')
    # 移除所有 r="颜色名"> 格式的标记，但保留 r="Maroon">
    text = re.sub(r'r="(?!Maroon")[^"]*">', '', text)
    return text

def filter_words(input_file=None, output_file=None):
    """
    过滤掉中英文搭配格式的行(英文单词:中文释义;中文释义)
    :param input_file: 输入文件路径，如果为None则从stdin读取
    :param output_file: 输出文件路径，如果为None则输出到stdout
    """
    pattern = WORD_DEF_PATTERN
    
    input_source = open(input_file, 'r') if input_file else sys.stdin
    output_dest = open(output_file, 'w') if output_file else sys.stdout
    
    for line in input_source:
        line = remove_color_tags(line.strip())
        if not pattern.match(line):  # 只保留不匹配的行
            output_dest.write(line + '\n')
            
    
    if input_file:
        input_source.close()
    if output_file:
        output_dest.close()
        
def interactive_filter():
    """交互式过滤模式"""
    print("进入交互式过滤模式(输入'exit'退出)")
    pattern = WORD_DEF_PATTERN
    
    print("提示：将过滤掉以下格式的行：")
    print("示例：word:释义 或 word:释义;释义")
    print("----------------------------------")
    
    while True:
        text = input("请输入要过滤的文本(可多行,空行结束):\n")
        if text.lower().strip() == 'exit':
            break
            
        # 处理多行输入
        lines = text.split('\n')
        filtered_lines = []
        for line in lines:
            line = remove_color_tags(line.strip())
            if line and not pattern.fullmatch(line):  # 只保留不匹配的行
                filtered_lines.append(line)
        
        if filtered_lines:
            print("\n过滤结果:")
            print('\n'.join(filtered_lines))
        else:
            print("(无有效内容)")

def run_test_case():
    """运行内置测试用例"""
    test_cases = [
        "puppet:木偶",  # 单个单词:释义
        "Jiminy:int.天啊(表示温和的惊讶所用感叹词); Cricket:板球(运动);蟋蟀",  # 多个单词:释义组合
        "cuddly:adj.令人想拥抱的",  # 单个带词性标注
        "Disney:n.迪斯尼(美国动画影片制作家及制片人) Walt:adj.空心的",  # 空格分隔的多个单词:释义
        "humble:adj.谦逊的;vt.使谦恭",  # 单个多释义
        "upbringing:n.教养;养育;抚育",  # 单个多释义
        "Kansas:n.堪萨斯州(美国州名)",  # 单个地名
        "iconic:adj.图标的,形象的",  # 单个带标点
        "Disneyland:迪士尼乐园",  # 单个专有名词
        "This should not be filtered",  # 不应被过滤的普通文本
        "Another normal sentence",  # 不应被过滤的普通文本
        "word1:释义1 word2:释义2 word3:释义3",  # 多个单词:释义组合
        "stern:n.船尾;末端;adj.严厉的;坚定的; sassed:n.(美)炖水果;vt.跟…顶嘴; doo-doo:n.大便; deserve:vi.应受,应得;vt.应受,应得; respect:n.尊敬,尊重;vt.尊敬,尊重; garbage:n.垃圾;废物; Disneyland:迪士尼乐园 bend over:俯身;折转;access:vt.使用;存取;接近;n.进入;使用权;通路; decent:adj.正派的;得体的;相当好的; health care:n.卫生保健;retire:n.退隐;v.(令)退职; (比赛等); security:n.安全; adj.安全的; earned:adj.挣得的;v.挣得;引起(earn的过去分词);",
        "puppet:木偶 Jiminy:int.天啊 Cricket:板球 cuddly:adj.令人想拥抱的 Disney:n.迪斯尼 Walt:adj.空心的 humble:adj.谦逊的 upbringing:n.教养 Kansas:n.堪萨斯州 iconic:adj.图标的 Disneyland:迪士尼乐园",  # 复杂组合测试用例
        "unions:n.工会; (union的复数) voluntarily:adv.自动地;以自由意志; rank:n.排; adj.讨厌的;vt.排列; paternalism:n.家长式统治,家长作风; ofcourse:当然 bit:小块,有点儿 fairly:adv.相当地;公平地;简直;company:n.公司;陪伴,同伴;连队;vi.交往;vt.陪伴;; well-known:adj.著名的;众所周知的;清楚明白的;core:n.核心;要点;果心;[计]磁心;vt.挖...的核;commitment:n.承诺;投入;保证;许诺; moral:n.寓意; adj.道德的; obligation:n.义务; (已承诺的或法律等规定的)义务; uncomm:adj.不寻常的;罕有的;adv.非常地; attitude:n.态度;看法;意见;姿势;"
    ]
    
    
    
    
    print("测试用例:")
    for case in test_cases:
        print(case)
    print("\n过滤结果:")
    
    pattern = WORD_DEF_PATTERN
    for case in test_cases:
        if not pattern.fullmatch(case.strip()):
            print(case)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='过滤掉中英文搭配格式的行')
    parser.add_argument('-i', '--input', help='输入文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径')
    parser.add_argument('--interactive', action='store_true', help='进入交互模式')
    parser.add_argument('--test', action='store_true', help='运行内置测试用例')
    args = parser.parse_args()
    
    if args.test:
        run_test_case()
    elif args.interactive:
        interactive_filter()
    else:
        filter_words(args.input, args.output)
