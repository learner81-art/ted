import re
import sys

def clean_content(input_file, output_file):
    # 定义要清理的模式
    color_pattern = re.compile(r'\[r=[^\]]+\>')
    explanation_pattern = re.compile(r'\[:[^\]]+\]')
    
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line in f_in:
            # 保留文件分段结构
            if line.startswith('==='):
                f_out.write(line)
                continue
                
            # 应用清理规则
            cleaned_line = color_pattern.sub('', line)  # 移除颜色标记
            cleaned_line = explanation_pattern.sub('', cleaned_line)  # 移除单词解释
            
            # 写入清理后的行
            f_out.write(cleaned_line)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python clean_content.py <input_file> <output_file>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    clean_content(input_file, output_file)
    print(f"Content cleaned and saved to {output_file}")
