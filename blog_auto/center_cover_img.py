import json
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont
from aip import AipOcr
from io import BytesIO
import qiniu
from logger import logger
from qiniu import CdnManager


def recognize_text_with_position(image):
    """
    百度OCR识别文本、位置
    :param image:
    :return: list(tuple(
                    tuple(文本到左边框距离，文本到顶部边框距离，文本宽度，文本高度),
                    tuple(文本中心点x距整个图片中心点x的距离，文本中心点y距整个图片中心点y的距离),
                    文本内容))
    """
    text_positions = []

    # 将图片转换为二进制数据
    with BytesIO() as output:
        image.save(output, format='PNG')
        img_byte_array = output.getvalue()

    # 调用百度 OCR 进行文字识别
    result = client.general(img_byte_array)

    if 'words_result' in result:
        image_width, image_height = image.size
        # 计算整个图片的中心点
        image_center_x = image_width / 2
        image_center_y = image_height / 2
        for item in result['words_result']:
            text = item['words']
            location = item['location']
            x, y, width, height = location['left'], location['top'], location['width'], location['height']
            # 计算文本内容的中心点
            text_center_x = x + width / 2
            text_center_y = y + height / 2
            # 计算文本中心点与整个图片的中心点距离
            threshold_x = abs(text_center_x - image_center_x)
            threshold_y = abs(text_center_y - image_center_y)

            text_positions.append(((x, y, x + width, y + height), (threshold_x, threshold_y), text))

    return text_positions

def get_categories_imgs(img_categorie_path):
    """
    获取本地的分类（也就是背景）图片
    :return:
    """
    img_categorie_dict = {}
    images = Path(img_categorie_path).iterdir()
    for local_image_path in images:
        img_categorie = str(local_image_path).split("/")[-1]
        if img_categorie == "bg.jpg":
            continue
        img_categorie_dict[img_categorie] = local_image_path
    return img_categorie_dict

def read_config(filepath):
    """
    读取配置
    """
    with open(filepath, 'r', encoding="utf-8") as file:
        return json.load(file)

def choice_png_replace(qiniu_domain_name,bucket,auth,choice,image_name,local_image_path):
    """
    选择图片进行替换
    :param qiniu_domain_name:
    :param bucket:
    :param auth:
    :param choice:
    :param image_name:
    :param local_image_path:
    :return:
    """
    # 本地图片覆盖七牛云图片
    if choice == "1":
        # 读取本地文件内容
        with open(local_image_path, "rb") as f:
            data = f.read()

        token = auth.upload_token(bucket, image_name)
        ret, info = qiniu.put_data(token, image_name, data)
        if ret is not None:
            logger.info("本地图片覆盖七牛云图片成功")
        else:
            logger.error("本地图片覆盖七牛云图片失败:", ret)

    # 七牛云图片覆盖本地图片
    elif choice == "2":
        url = f"http://{qiniu_domain_name}/{image_name}"
        response = requests.get(url)
        if response.status_code == 200:
            with open(local_image_path, "wb") as f:
                f.write(response.content)
            logger.info("七牛云图片覆盖本地图片成功")
        else:
            logger.error("七牛云图片覆盖本地图片失败")

    else:
        logger.info("操作取消")

def drawblank():
    """
    绘制底色
    """
    img = Image.new('RGB', (373, 251), (255, 255, 255))
    img.save(f'{img_categorie_path}bg.jpg')

def save_text(categorie, img_categorie_path, content=None):
    """
    背景图（在空白图片上添加文字）
    :param categories: 图片名（默认为目录名）
    :param img_categorie_path: 目录名的路径
    :param content: 图片内容（可传可不传，有值时按照值绘制内容）
    :return:
    """
    ttfont = ImageFont.truetype("config/simhei.ttf", 50)  # 这里我之前使用Arial.ttf时不能打出中文，用华文细黑就可以
    if not Path(f"{img_categorie_path}bg.jpg").exists():
        drawblank()

    im = Image.open(f"{img_categorie_path}bg.jpg")
    draw = ImageDraw.Draw(im)

    # 计算居中位置并将文字绘入
    text = categorie if not content else content
    text_bbox = draw.textbbox((0, 0), text, font=ttfont)
    image_width, image_height = im.size
    x = (image_width - text_bbox[2]) // 2
    y = (image_height - text_bbox[3]) // 2
    draw.text((x, y), text, fill=(0, 0, 0), font=ttfont)

    img_save_path = f'{img_categorie_path}{categorie}.png'
    im.save(img_save_path)
    return img_save_path

def compare_image_content_location(img_categorie_path,img_categorie_dict):
    """
    比较图像内容、位置
    :param img_categorie_path:
    :param img_categorie_dict:
    :return:
    """
    # cover配置文件
    config_data = read_config('config/config.json')
    cover_urls = config_data["cover"]
    # 七牛云配置文件
    upload_config_data = read_config('config/upload_config.json')
    access_key = upload_config_data["七牛云"]["access_key"]
    secret_key = upload_config_data["七牛云"]["secret_key"]
    qiniu_domain_name = upload_config_data["七牛云"]["qiniu_domain_name"]
    bucket = upload_config_data["七牛云"]["bucket"]
    auth = qiniu.Auth(access_key, secret_key)
    cdn_manager = CdnManager(auth)
    # 刷新七牛云CDN链接
    cover_list = list(cover_urls.values())
    ret,info = cdn_manager.refresh_urls(cover_list)
    if ret is not None:
        logger.info("刷新 CDN 缓存成功")
    else:
        logger.error("刷新 CDN 缓存失败:", info)

    threshold = 4  # 设置一个阈值，判断文字中心坐标是否在图片中心附近
    for image_name, local_image_path in img_categorie_dict.items():
        categorie = image_name.split(".")[0]
        # 如果cover配置存在
        if categorie in cover_urls:
            qiniu_image_url = cover_urls[categorie]
            logger.info(f"本地文件：{local_image_path}，七牛链接：{qiniu_image_url}")

            # 加载本地图片和七牛云图片
            local_image = Image.open(local_image_path)
            qiniu_image_response = requests.get(qiniu_image_url)
            qiniu_image = Image.open(BytesIO(qiniu_image_response.content))

            local_text_positions = recognize_text_with_position(local_image)
            time.sleep(1)
            qiniu_text_positions = recognize_text_with_position(qiniu_image)

            if local_text_positions is None:
                logger.info(f"本地图片：{local_text_positions}，未识别出来")
                continue
            elif qiniu_text_positions is None:
                logger.info(f"七牛云图片：{qiniu_text_positions}，未识别出来")
                continue
            else:
                logger.info(f"本地图片：{local_text_positions}，七牛云图片：{qiniu_text_positions}")

            # 比较文字内容和位置信息
            for local_position, local_threshold, local_text in local_text_positions:
                for qiniu_position, qiniu_threshold, qiniu_text in qiniu_text_positions:
                    # 内容一致
                    if local_text == qiniu_text:
                        if local_position != qiniu_position:
                            logger.info("图片内部文字相同但位置不一致")
                            local_center_status = all(value <= threshold for value in local_threshold)
                            qiniu_center_status = all(value <= threshold for value in qiniu_threshold)
                            if local_center_status:
                                choice_png_replace(qiniu_domain_name,bucket,auth,"1", image_name, local_image_path)
                            elif qiniu_center_status:
                                choice_png_replace(qiniu_domain_name,bucket,auth,"2", image_name, local_image_path)
                            else:
                                # 先覆盖本地
                                img_save_path = save_text(categorie, img_categorie_path)
                                # 再覆盖七牛云
                                choice_png_replace(qiniu_domain_name,bucket,auth,"1", image_name, img_save_path)
                        else:
                            logger.info("图片内部文字相同且位置一致")
                            center_status = all(value <= threshold for value in local_threshold)
                            if center_status:
                                logger.info("已居中")
                            else:
                                logger.info("未居中")
                                # 先覆盖本地
                                img_save_path = save_text(categorie, img_categorie_path)
                                # 再覆盖七牛云
                                choice_png_replace(qiniu_domain_name,bucket,auth,"1", image_name, img_save_path)
                    else:
                        logger.info("图片内部文字不同")
                        option_text = input(f"经识别此次图片文字不一致，请选择保留哪一个：1.{local_text}，2.{qiniu_text}：")

                        # 选本地
                        if option_text == 1:
                            center_status = all(value <= threshold for value in local_threshold)
                            # 居中，覆盖七牛图
                            if center_status:
                                choice_png_replace(qiniu_domain_name,bucket,auth,"1", image_name, local_image_path)
                            # 不居中，通过生成新图覆盖本地和七牛云
                            else:
                                # 先覆盖本地
                                img_save_path = save_text(categorie, img_categorie_path)
                                # 再覆盖七牛云
                                choice_png_replace(qiniu_domain_name,bucket,auth,"1", image_name, img_save_path)
                        # 选线上
                        elif option_text == "2":
                            center_status = all(value <= threshold for value in qiniu_threshold)
                            # 居中，下载七牛图来覆盖本地文件
                            if center_status:
                                choice_png_replace(qiniu_domain_name,bucket,auth,"2", image_name, local_image_path)
                            # 不居中，通过生成新图覆盖本地和七牛
                            else:
                                # 先覆盖本地
                                img_save_path = save_text(categorie, img_categorie_path)
                                # 再覆盖七牛云
                                choice_png_replace(qiniu_domain_name,bucket,auth,"1", image_name, img_save_path)
                        else:
                            logger.info("选项错误，图片取消")

        else:
            logger.info(f"本地文件：{local_image_path}，未在配置文件找到链接")


if __name__ == '__main__':
    # 分类图片目录
    img_categorie_path = "./img/"
    img_categorie_dict = get_categories_imgs(img_categorie_path)

    # 百度 OCR
    ocr_data = read_config("config/OCR_config.json")["百度OCR"]
    client = AipOcr(ocr_data["APP_ID"], ocr_data["API_KEY"], ocr_data["SECRET_KEY"])

    compare_image_content_location(img_categorie_path,img_categorie_dict)

