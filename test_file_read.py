import os

def test_file_read(file_path):
    try:
        # 检查文件大小
        size = os.path.getsize(file_path)
        print(f"文件大小: {size} 字节")
        
        # 尝试不同编码方式读取
        encodings = ['utf-8', 'gbk', 'latin-1', 'ascii']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read(100)
                    print(f"\n使用 {encoding} 编码读取成功:")
                    print(content)
                    return
            except UnicodeDecodeError:
                print(f"\n使用 {encoding} 编码读取失败")
            except Exception as e:
                print(f"\n使用 {encoding} 编码读取时出错: {str(e)}")
                
        # 如果文本编码都失败，尝试二进制读取
        with open(file_path, 'rb') as f:
            binary = f.read(100)
            print("\n二进制内容(前100字节):")
            print(binary)
            
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    test_file_read("full_pdf_content.txt")
