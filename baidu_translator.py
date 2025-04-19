from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def translate_text(text, source_lang="auto", target_lang="zh"):
    # 设置浏览器选项
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # 无头模式
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # 初始化浏览器
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    try:
        # 打开百度翻译页面
        driver.get("https://fanyi.baidu.com/mtpe-individual/multimodal?aldtype=16047&ext_channel=Aldtype#/auto/zh")
        
        # 等待输入区域加载完成
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "editor-text"))
        )
        
        # 输入待翻译文本
        input_area = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "editor-text"))
        )
        input_area.click()  # 先点击激活输入框
        input_area.clear()
        input_area.send_keys(text)
        
        # 等待翻译完成 - 检查结果区域是否有内容
        WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.CSS_SELECTOR, ".target-output").text.strip() != ""
        )
        
        # 获取翻译结果 - 使用用户提供的DOM元素
        result_area = driver.find_element(By.CSS_SELECTOR, ".target-output")
        translated_text = result_area.text
        
        return translated_text
        
    except Exception as e:
        print(f"翻译过程中出错: {str(e)}")
        return None
        
    finally:
        driver.quit()

if __name__ == "__main__":
    text_to_translate = input("请输入要翻译的文本: ")
    result = translate_text(text_to_translate)
    print("\n翻译结果:")
    print(result)
