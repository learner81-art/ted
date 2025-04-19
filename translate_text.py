#!/usr/bin/env python3
import os
import subprocess
import time

def translate_text(text):
    """
    使用AppleScript调用欧路词典翻译文本
    :param text: 要翻译的文本
    :return: 翻译结果
    """
    try:
        # 使用剪贴板方式获取翻译结果
        import pyperclip
        
        # 保存当前剪贴板内容
        original_clipboard = pyperclip.paste()
        
        try:
            # 检查应用程序是否存在并启动
            # 使用用户提供的绝对路径检查应用
            app_path = "/Applications/Eudb_en_free.app"
            check_script = f'''
            try
                tell application "Finder"
                    get application file ((POSIX file "{app_path}") as text)
                end tell
                return true
            on error
                return false
            end try
            '''
            
            app_exists = subprocess.run(['osascript', '-e', check_script], 
                                     capture_output=True, 
                                     text=True).stdout.strip() == 'true'
            
            if not app_exists:
                return f"欧路词典未找到。请确认: \n1. 应用已安装在{app_path}\n2. 应用名称拼写正确\n3. 尝试手动打开应用确认是否正常工作"
            
            # 构建AppleScript命令
            app_name = "Eudb_en_free"  # 应用程序名称(不带.app后缀)
            script = f'''
            tell application "{app_name}"
                activate
                delay 0.5
                set the clipboard to "{text}"
                delay 0.5
                tell application "System Events" to keystroke "v" using command down
                delay 0.5
                tell application "System Events" to keystroke return
                delay 1.0
            end tell
            '''
            
            # 执行AppleScript
            subprocess.run(['osascript', '-e', script], check=True)
            
            # 获取翻译结果
            time.sleep(1)  # 等待词典处理
            
            # 尝试直接从欧路词典窗口获取翻译结果
            get_result_script = f'''
            tell application "System Events"
                tell process "{app_name}"
                    set frontmost to true
                    delay 1
                    try
                        set resultText to value of text area 1 of scroll area 1 of window 1
                        return resultText
                    on error
                        return ""
                    end try
                end tell
            end tell
            '''
            
            translated = subprocess.run(['osascript', '-e', get_result_script],
                                     capture_output=True, 
                                     text=True).stdout.strip()
            
            # 恢复原始剪贴板内容
            pyperclip.copy(original_clipboard)
            
            if not translated:
                return "翻译成功(请查看欧路词典窗口)"
            
            # 简单清理翻译结果
            translated = translated.strip()
            if len(translated) > 1000:  # 防止返回过大内容
                translated = translated[:1000] + "...(内容截断)"
                
            return translated if translated else "未能获取翻译结果"
            
        except Exception as e:
            pyperclip.copy(original_clipboard)
            return f"翻译失败: {str(e)}"
        
    except Exception as e:
        return f"翻译失败: {str(e)}"

def clean_input(text):
    """清理用户输入的特殊字符和多余空格"""
    import re
    text = re.sub(r'[^\w\s]', '', text)  # 移除非字母数字和空格字符
    text = re.sub(r'\s+', ' ', text)     # 合并多个空格
    return text.strip()

if __name__ == "__main__":
    try:
        text = input("请输入要翻译的文本: ")
        text = clean_input(text)
        if not text:
            print("错误: 输入不能为空")
        else:
            result = translate_text(text)
            print(result)
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        print(f"程序错误: {str(e)}")
