import os
import pdfplumber
from datetime import datetime

def extract_pdf_text(pdf_path):
    """提取单个PDF文本内容"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n\n"
            return text
    except Exception as e:
        print(f"处理PDF出错 {pdf_path}: {str(e)}")
        return None

def batch_process_pdfs(input_dir, output_file):
    """批量处理目录下所有PDF文件"""
    if not os.path.exists(input_dir):
        print(f"目录不存在: {input_dir}")
        return False

    processed_count = 0
    with open(output_file, 'w', encoding='utf-8') as out_f:
        # 写入文件头
        out_f.write(f"PDF内容提取报告\n")
        out_f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out_f.write(f"源目录: {input_dir}\n")
        out_f.write("="*50 + "\n\n")

        # 遍历处理PDF文件
        for filename in sorted(os.listdir(input_dir)):
            if filename.lower().endswith('.pdf'):
                filepath = os.path.join(input_dir, filename)
                out_f.write(f"=== 文件: {filename} ===\n")
                
                content = extract_pdf_text(filepath)
                if content:
                    out_f.write(content + "\n")
                    processed_count += 1
                else:
                    out_f.write(f"[处理此文件时出错]\n")
                
                out_f.write("="*50 + "\n\n")

    print(f"已处理 {processed_count} 个PDF文件，结果保存到 {output_file}")
    return True

if __name__ == "__main__":
    # 配置路径
    pdf_dir = "../已读"  # PDF文件目录
    output_path = "pdf_contents_combined.txt"  # 输出文件
    
    # 执行处理
    batch_process_pdfs(pdf_dir, output_path)
