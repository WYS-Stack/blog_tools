import re
from functools import partial

# pattern = r"https://\S*\.(?:jpg|png|jpeg)|^/Users/wanghan/.*\.(jpg|png|jpeg)$"
pattern = r"/Users/wanghan/.*\.(jpg|png|jpeg)$"


# 测试字符串
test_strings = [
    "/Users/wanghan/asdas/some_image.png",
    "/Users/wanghan/qer2er/sdfdsf/another_image.jpg",
    "/Users/wanghan/qweqwas/sasdqsd/qweqwe/yet_another.jpeg",
    "/Users/wanghan/not_an_image.txt",
    "https://images.cherain-wh.cloud/conda.png",
    "https://images.cherain-wh.cloud/%E5%A4%96%E5%8C%BA.png",
    "https://images.cherain-wh.cloud/MySQL.png",
    "/Users/wanghan/Desktop/code/project_test/blog_tools/blog_auto/img/外区.png"
]

# 替代的字符串
def replace_image_domain(match_url):
    link = match_url.group()
    print(link)
    return "REPLACEMENT_STRING"

file = "/Users/wanghan/Desktop/code/project_test/blog_tools/test/外区/【2023年】五分钟注册美区AppleID，手把手教，稳定且耐用！.md"
with open(file, 'r+') as f:
    lines = f.readlines()
    # 对匹配到的结果进行处理并替换 为本地路径
    for line in lines:
        # 返回替换后的结果、检测到的URL数量
        replaced_result, replaced_count = re.subn(pattern,
                                                  replace_image_domain, line)
