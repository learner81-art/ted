import re

def filter_text(text):
    # 过滤时间标记
    text = re.sub(r'\[\d{2}:\d{2}\]', '', text)
    # 保留中文、标点和空格(包括中文姓名点号·)
    text = re.sub(r'[^\u4e00-\u9fa5，。、；：？！“”‘’（）【】…—《》〈〉·\s-]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

test_text = """他的名字是罗伊·欧.迪士尼, 与他的兄弟沃尔特·迪士尼 在堪萨斯的一个 非常普通的环境中长大, 后来创建并经营了世界上 最具标志性的商业品牌之一。
[01:13]
Two things I remember the best about going to Disneyland with my grandfather.
有两件与祖父一起去迪斯尼乐园的事 给我留下了"""

filtered_text = filter_text(test_text)
print("过滤结果:")
print(filtered_text)
