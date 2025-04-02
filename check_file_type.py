import os
import magic

def check_file_type(file_path):
    try:
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        print(f"文件大小: {file_size} 字节")
        
        # 使用python-magic检测文件类型
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)
        print(f"实际文件类型: {file_type}")
        
        # 尝试读取前100字节
        with open(file_path, 'rb') as f:
            content = f.read(100)
            print(f"前100字节(十六进制): {content.hex()}")
            
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    check_file_type("full_pdf_content.txt")
