import sys
import click
from pathlib import Path
from logger import logger

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_dir))

from blog_auto.blog_auto_tool import Blog_Tool


# @click.command()
# @click.option('--status', type=click.Choice(['y', 'yes', 'no', 'n']),
#               prompt=click.style("为避免脚本修改文件把博客未提交文件的git缓存覆盖！！！\n请确认是否已提交代码？yes/no: ",fg='red'))
def main():
    bt = Blog_Tool(filepath, img_categorie_path, download_img_path)
    # # 当背景图片需要自定义时
    # bt.save_text("图片名称","图片内容")

    # 自动git提交并检测是否有未提交的文件
    bt.git_commit()
    logger.info("==========开始执行==========")
    # 自动扫描Hexo文件夹下的目录
    bt.blog_dirs()
    # 获取分类图片
    bt.get_categories_imgs()
    # 对文件进行添加或修改头部内容
    bt.add()
    # 保存文件内新增的图片到本地
    bt.download_image_to_local()
    # 部署到服务器
    bt.deploy_server()
    logger.info("==========执行结束==========")


if __name__ == '__main__':
    # Hexo博客目录
    filepath = "/Users/wanghan/Desktop/code/blog/source/_posts/"
    # 分类图片目录
    img_categorie_path = "./img/"
    # 博客内含图片下载目录
    download_img_path = "/Users/wanghan/Desktop/图片/blog/"

    # 测试使用

    # filepath = "../test/"
    # img_categorie_path = "./img/"
    # download_img_path = "../img/"

    main()
