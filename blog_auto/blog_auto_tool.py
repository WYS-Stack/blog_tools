import json
import math
import os
import re
import subprocess
import urllib.parse
from datetime import datetime
from pathlib import Path

import qiniu
import requests
import send2trash
import urllib3
from PIL import Image, ImageDraw, ImageFont

from blog_auto.config.historical_data import old_data
from logger import logger


class Blog_Tool():
    """
    向有道云导出笔记中 添加 Hexo的标题和创建时间
    """

    def __init__(self, filepath, img_categorie_path, download_img_path):
        self.filepath = filepath
        # 源代码路径
        source_filepath_match = re.match(r"(.*/)(?:source/.*$)", filepath)
        self.source_filepath = source_filepath_match.group(1) if source_filepath_match else None
        self.upfilename = []
        self.one_dirs = Path(self.filepath).iterdir()
        self.img_categorie_path = img_categorie_path
        self.download_img_path = download_img_path
        self.config_filepath = 'config/config.json'
        self.upload_config_filepath = 'config/upload_config.json'

        self.config_data = self.read_config(self.config_filepath)
        self.f_Unexecuted = self.config_data["Unexecuted_files"]
        self.upload_config_data = self.read_config(self.upload_config_filepath)

        self.password_formats = ["theme: ", "abstract: ", "password: "]
        self.MAX_ATTEMPTS = 3
        self.VALID_OPTIONS = ["y", "yes", "n", "no"]
        self.length = 0
        self.download_img_length = 0
        self.download_img_length_error = 0
        self.remove_file_num = 0
        self.Unexecuted_file_num = 0
        self.Unexecuted_file_add = 0
        self.file_list = []
        self.img_categorie_list = []

        self.total_ = """\
---
"""
        self.md_title = """\
title: {filename}
"""
        self.lengthen_md_title = """\
title: >-
  {filename}\
"""
        self.md_date = """\
date: {updatetime}
"""
        self.md_categories = """\
categories: {categories}
"""
        self.md_tags = """\
tags: {tags}
"""
        self.md_cover = """\
cover: '{cover}'
"""
        self.md_addrlink = "\n"

        self.md_theme = """\
theme: Xray
"""
        self.md_abstract = """\
abstract: Welcome to my blog, enter password to read. 
"""
        self.md_password = """\
password: wanghan...
"""

    def blog_dirs(self):
        """
        循环遍历找出博客路径下的所有文件
        file_list：存储所有的文件
        """
        for onedir in self.one_dirs:
            if onedir.is_dir():
                self.one_dirs = onedir.iterdir()
                self.blog_dirs()
            else:
                onedir = str(onedir)
                total_filename = onedir.split("/")[-1]
                # 过滤不需要上传的文件
                ignore_files = self.config_data["ignore_files"]
                if total_filename in ignore_files:
                    continue
                suffix = total_filename.split(".")[-1]
                # 过滤非md文件 且 不在非执行文件"Unexecuted_files"配置 内的文件
                if suffix == "md":
                    self.file_list.append(onedir)
                elif onedir in self.f_Unexecuted:
                    self.Unexecuted_file_num += 1
                else:
                    confirm = input(f"是否添加文件：{onedir}到不必执行文件（y，yes，no）：")
                    if confirm in ["y", "yes"]:
                        self.write_config(self.config_filepath,"Unexecuted_files",onedir)
                        self.Unexecuted_file_add += 1
                    else:
                        logger.info(f"未执行文件（非md）：{onedir}")

    def get_categories_imgs(self):
        """
        获取本地的分类（也就是背景）图片
        :return:
        """
        images = Path(self.img_categorie_path).iterdir()
        for img in images:
            img_categories = str(img).split("/")[-1].split(".")[0]
            self.img_categorie_list.append(img_categories)

    def drawblank(self):
        """
        生成一张空白图片
        """
        img = Image.new('RGB', (373, 251), (255, 255, 255))
        img.save(f'{self.img_categorie_path}bg.jpg')

    def save_text(self, categorie, content=None):
        """
        背景图（在空白图片上添加文字）
        :param categorie: 图片名（默认为目录名）
        :param content: 图片内容（可传可不传，有值时按照值绘制内容）
        :return:
        """
        ttfont = ImageFont.truetype("config/simhei.ttf", 50)  # 这里我之前使用Arial.ttf时不能打出中文，用华文细黑就可以
        if not Path(f"{self.img_categorie_path}bg.jpg").exists():
            self.drawblank()
        im = Image.open(f"{self.img_categorie_path}bg.jpg")
        draw = ImageDraw.Draw(im)
        # 将文字居中绘入
        text = categorie if not content else content
        text_bbox = draw.textbbox((0, 0), text, font=ttfont)
        image_width, image_height = im.size
        x = (image_width - text_bbox[2]) // 2
        y = (image_height - text_bbox[3]) // 2
        draw.text((x, y), text, fill=(0, 0, 0), font=ttfont)

        img_save_path = f'{self.img_categorie_path}{categorie}.png'
        im.save(img_save_path)
        return img_save_path

    def qiniu_upload(self, img_name, img_file_path):
        """
        七牛云上传背景cover图片
        :param img_name: 上传图片名
        :param img_file_path: 上传图片路径
        :return:
        """
        access_key = self.upload_config_data["七牛云"]["access_key"]
        secret_key = self.upload_config_data["七牛云"]["secret_key"]
        qiniu_domain_name = self.upload_config_data["七牛云"]["qiniu_domain_name"]
        bucket = self.upload_config_data["七牛云"]["bucket"]

        q = qiniu.Auth(access_key, secret_key)
        # 匹配所有中文字符，\u4e00 对应第一个中文字符 "一"，\u9fa5 对应最后一个中文字符 "龥"
        pattern = re.compile(r'[\u4e00-\u9fa5]')

        # 先检查七牛云上是否已经存在同名的图片
        bucket_manager = qiniu.BucketManager(q)
        ret, info = bucket_manager.stat(bucket, img_name)
        if ret:
            contains_chinese = bool(pattern.search(img_name))
            if contains_chinese:
                # 转换为URL编码格式
                img_name = urllib.parse.quote(img_name)
            url = 'https://{0}/{1}'.format(qiniu_domain_name, img_name)
            # 如果文件已经存在，直接返回链接
            return url

        token = q.upload_token(bucket, img_name)
        ret, info = qiniu.put_file(token, img_name, img_file_path)
        if ret:
            contains_chinese = bool(pattern.search(ret['key']))
            if contains_chinese:
                ret['key'] = urllib.parse.quote(ret['key'])
            return 'https://{0}/{1}'.format(qiniu_domain_name, ret['key'])
        else:
            logger.error("背景图片上传失败，请手动重试!!!")
            return '上传失败，请重试'

    def read_file(self, file, filename, updatetime, categorie, tags, cover):
        with open(file, 'r+') as f:
            content = f.readlines()
            md_title = self.md_title.format(filename=filename)
            content_index = [2, 3, 4, 5, 6, 7]
            # 将标题长度大于77个字符的进行换行处理
            if len(filename) >= 77:
                lengthen_filename = filename[0:77]
                for i in range(1, math.ceil(len(filename) / 77)):
                    lengthen_filename = lengthen_filename + "\n" + "  " + filename[77 * i + 1:77 * (i + 1)]
                md_title = self.lengthen_md_title.format(filename=lengthen_filename)
                content_index = list(map(lambda x: x + math.ceil(len(filename) / 77), content_index))

            md_date = self.md_date.format(updatetime=updatetime)
            md_categories = self.md_categories.format(categories=categorie)
            md_tags = self.md_tags.format(tags=tags)
            md_cover = self.md_cover.format(cover=cover)

            try:
                # 第一种情况：有头部信息 但头部信息内容不对
                if content[0] == self.total_:
                    flag = False
                    if len(filename) < 77:
                        if content[1] != md_title:
                            content[1] = md_title
                            flag = True
                    # 对于标题长度大于77个字符的逐行替换
                    else:
                        if ''.join(content[1:content_index[0]]) != md_title + "\n":
                            for title_index in zip(range(1, math.ceil(len(filename) / 77) + 2),
                                                   range(0, math.ceil(len(filename) / 77) + 1)):
                                content[title_index[0]] = md_title.split("\n")[title_index[1]] + "\n"
                            flag = True
                    if content[content_index[0]] != md_categories:
                        content[content_index[0]] = md_categories
                        flag = True
                    if content[content_index[1]] != md_tags:
                        content[content_index[1]] = md_tags
                        flag = True
                    if content[content_index[2]] != md_cover:
                        content[content_index[2]] = md_cover
                        flag = True
                    if "abbrlink: " in content[content_index[3]] or content[content_index[3]] == self.md_addrlink:
                        content[content_index[3]] = content[content_index[3]]
                    else:
                        content[content_index[3]] = self.md_addrlink
                        flag = True
                    # 由于先前操作错误导致本地文件时间信息变动，因此放弃了修改已经存在时间的文件
                    if content[content_index[4]] != md_date and "date: " not in content[content_index[4]]:
                        content[content_index[4]] = md_date
                        flag = True
                    if content[content_index[5]] != self.total_:
                        if content[content_index[5]] == self.md_theme and content[
                            content_index[5] + 1] == self.md_abstract and content[
                            content_index[5] + 2] == self.md_password:
                            if content[content_index[5] + 3] != self.total_:
                                content[content_index[5] + 3] = self.total_
                                flag = True
                        elif any(password_format in content[content_index[5]] for password_format in
                                 self.password_formats) \
                                and any(password_format in content[content_index[5] + 1] for password_format in
                                        self.password_formats) \
                                and any(password_format in content[content_index[5] + 2] for password_format in
                                        self.password_formats):
                            if content[content_index[5] + 3] != self.total_:
                                content[content_index[5] + 3] = self.total_
                                flag = True
                        else:
                            content[content_index[5]] = self.total_
                            flag = True
                    if flag:
                        self.length += 1
                        self.upfilename.append(filename)
                # 第二种情况：没有头部信息 但有文章信息（使用文章头部信息倒插的方式进入整篇文章）
                else:
                    content.insert(0, self.total_)
                    content.insert(0, md_date)
                    content.insert(0, self.md_addrlink)
                    content.insert(0, md_cover)
                    content.insert(0, md_tags)
                    content.insert(0, md_categories)
                    content.insert(0, md_title)
                    content.insert(0, self.total_)
                    self.length += 1
                    self.upfilename.append(filename)
            # 第三种情况：没有头部信息 也没有文章信息
            except IndexError:
                content.extend([self.total_, md_title, md_categories, md_tags, md_cover, self.md_addrlink, md_date,
                                self.total_])
                self.length += 1
                self.upfilename.append(filename)
            finally:
                with open(file, 'w+') as new_file:
                    new_file.writelines(content)

    def modification_date(self, filename):
        """
        对于近期新增文件进行文件的创建时间获取
        :param filename:
        :return:
        """
        t = os.stat(filename).st_birthtime
        return datetime.strftime(datetime.fromtimestamp(t), "%Y-%m-%d %H:%M:%S")

    def read_config(self,filepath):
        """
        读取背景配置
        """
        with open(filepath, 'r', encoding="utf-8") as file:
            return json.load(file)

    def write_config(self, filepath, key, value, categories=None):
        """
        写入背景配置
        :return:
        """
        if key == "cover":
            self.config_data[key][f"{categories}"] = f"{value}"
        elif key == "Unexecuted_files":
            self.config_data[key].append(f"{value}")
        with open(filepath, 'w', encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=4, ensure_ascii=False)

    def add(self):
        """
        对Hexo博客下所有文件添加标题和时间

            file: 整个文件路径
            total_filename：整个文件名
            filename：文件名，不包含后缀
            suffix: 文件名后缀
            updatetime：文件创建时间
            categories：文件分类
            tags：文件标签
            cover：文件背景图
        """
        for file in self.file_list:
            total_filename = file.split("/")[-1]
            filename = total_filename.rsplit(".", 1)[0]
            if old_data.get(total_filename):
                updatetime = old_data[total_filename]['createtime']
            else:
                updatetime = self.modification_date(file)
            categories = file.split(self.filepath)[-1].split("/")[0]
            tags = "-".join(file.split(self.filepath)[-1].split("/")[0:-1])
            # 如果分类不在本地的分类图片中
            if categories not in self.img_categorie_list:
                # 先绘制分类背景图
                img_save_path = self.save_text(categories)
                # 再上传分类背景图片
                img_upload_url = self.qiniu_upload(categories + ".png", img_save_path)
                # 最后写入配置
                self.write_config(self.config_filepath, "cover",img_upload_url,categories)
            else:
                if categories not in self.config_data["cover"]:
                    # 先上传
                    img_upload_url = self.qiniu_upload(categories + ".png",
                                                       f'{self.img_categorie_path}{categories}.png')
                    # 最后写入配置
                    self.write_config(self.config_filepath,"cover",img_upload_url,categories)

            cover_data = self.config_data["cover"]
            if categories in cover_data.keys():
                cover = cover_data[categories]
            else:
                cover = ""

            self.read_file(file, filename, updatetime, categories, tags, cover)

        if self.length > 0:
            logger.info(f"修改-文件名称：{self.upfilename}")

    def delete_redundant_directories(self):
        """
        删除博客对应不存在的图片文件夹（因本地md文件所创建的图片文件夹）
        :return:
        """
        try:
            dir_list = Path(self.download_img_path).glob("**")
            remove_list = []
            for onedir in dir_list:
                onedir = str(onedir)
                img_dir = onedir.replace(self.download_img_path, self.filepath)
                if not Path(img_dir).exists():
                    remove_list.append(onedir)
            for remove_file in remove_list:
                self.remove_file_num = self.remove_file_num + sum(
                    [os.path.isfile(listx) for listx in os.listdir(remove_file)])
                # 删除文件到垃圾桶
                send2trash.send2trash(remove_file)
                # # 永久删除，无法找回
                # shutil.rmtree(remove_file,ignore_errors=True)
                # 删除未在博客发现，但本地存在的图片文件夹
                logger.info(f"删除-图片文件夹（本地不存在）：{remove_file}")
            logger.info(f"汇总："
                        f"修改文件数量：{self.length}，"
                        f"下载图片数量：{self.download_img_length}，"
                        f"下载失败数量：{self.download_img_length_error}，"
                        f"删除图片数量：{self.remove_file_num}，"
                        f"已知未执行文件数量：{self.Unexecuted_file_num}，"
                        f"新增未执行文件数量：{self.Unexecuted_file_add}")
        except Exception as e:
            logger.info(e)

    def download_image_to_local(self):
        """
        下载markdown文件里包含的图片到本地

        file_image_path：文件内图片的路径
        image_links：图片的链接
        :return:
        """
        # 防止使用测试路径时，会删除项目上下载的图片
        if self.filepath != "/Users/wanghan/Desktop/code/blog/source/_posts/":
            logger.error("原始博客路径不对，不给予下载！！！")
            exit()

        session = requests.session()
        # 测试添加
        urllib3.disable_warnings()
        for file in self.file_list:
            # 根据图片在之前markdown的路径，再保存图片的路径生成对应的目录
            download_img_path = file.replace(self.filepath, self.download_img_path) + "/"
            if not os.path.exists(download_img_path):
                os.makedirs(download_img_path)

            with open(file, 'r+') as f:
                file_data = f.read()
                # 匹配背景图（是以 https://***/ 开头，并以 .jpg 或 .png .jpeg 结尾的字符串）
                # 经过缩小的图片（例如：<img src="https://images.cherain-wh.cloud/50B582E5-12D6-4BAF-BA2B-D0A4C871F372_1_201_a.jpeg" width=200/>）
                pattern = r'https://\S*\.(?:jpg|png|jpeg)'
                img_links = re.findall(pattern, file_data)
            if img_links:
                for link in img_links:
                    img_name = link.split("/")[-1]
                    img_path = download_img_path + img_name
                    # 判断图片是否已存在 且 过滤是否是分类背景图
                    if not os.path.exists(img_path) and link not in self.config_data["cover"].values():

                        try:
                            # 下载图片
                            headers = {'Connection': 'close'}
                            response = session.get(link, headers=headers, verify=False)
                            if response.status_code == 200:
                                logger.info(f"下载-图片-文件：{file}")
                                logger.info(f"下载-图片-链接：{link}")
                                with open(img_path, 'wb') as f:
                                    f.write(response.content)
                                self.download_img_length += 1
                            else:
                                logger.error(f"下载-图片-失败：{response.status_code} - {file}")
                                self.download_img_length_error += 1
                        except requests.RequestException as e:
                            # 生成生成器。查看图片源路径下有没有名为"img_name"的
                            search_path = Path(self.download_img_path).rglob(img_name)
                            # 在生成器中依次寻找，找到返回，否则为None
                            file_in_path = next(search_path, None)
                            if file_in_path:
                                logger.info(f"下载-图片-本地迁移")
                                # 移动文件位置
                                file_in_path.rename(img_path)
                                self.download_img_length += 1
                            else:
                                self.download_img_length_error += 1
                                logger.error(f"下载-图片-发生错误：{e} - {file}")
                                logger.error(f"请手动下载图片：{link}，至：{img_path}")
        self.delete_redundant_directories()

    def git_detection_not_submit(self,status):
        """
        git检测博客修改且未提交文件
        :return:
        """
        # 判断是否有需要提交的文件
        result = subprocess.run(['git', 'status', '--porcelain'], cwd=self.source_filepath, capture_output=True,
                                text=True)
        commit_status = bool(result.stdout.strip())
        if commit_status:
            logger.info("==========检测到修改未提交==========")
            if status == "新增内容":
                # 获取修改但未提交的文件列表
                file_changes = {
                    ' M': '修改',
                    'M ': '修改',
                    ' A': '新增',
                    'A ': '新增',
                    ' D': '删除',
                    'D ': '删除',
                    '??': '未跟踪'
                }

                logger.info("git变化如下：")
                for file_status in result.stdout.split('\n'):
                    prefix = file_status[:2]
                    if prefix in file_changes:
                        action = file_changes[prefix]
                        file_name = file_status[2:].strip()
                        if file_name.endswith(".html") or file_name.endswith(".xml") or file_name.endswith(".txt"):
                            continue
                        logger.info(f"{action}的文件：{file_name}")

        return commit_status

    def get_user_input(self, prompt):
        """
        获取用户输入并验证是否为有效选项
        """
        while True:
            user_input = input(prompt)
            user_input_lower = user_input.lower()
            if user_input_lower in self.VALID_OPTIONS:
                return user_input_lower
            else:
                logger.info(f"==========请输入有效选项（y，yes，n，no）==========")

    def git_commit(self, git_commit_help="新增内容"):
        """
        是否帮助进行代码提交
        :return:
        """
        confirm_attempts = 0
        output = self.git_detection_not_submit(status=git_commit_help)
        while confirm_attempts < self.MAX_ATTEMPTS and output:
            git_status = self.get_user_input(f"{git_commit_help}是否帮助进行代码提交：（y，yes，n，no）:")
            if git_status in ["y", "yes"]:
                # git add .
                add_git = subprocess.Popen(['git', 'add', '.'], cwd=self.source_filepath, stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL)
                add_git_return_code = add_git.wait()
                # 超时和执行失败时给予警告
                if add_git_return_code is None or add_git_return_code != 0:
                    logger.error("==========git add失败==========")
                else:
                    # git commit -m 'up'
                    commit_git = subprocess.Popen(['git', 'commit', '-m', f'{git_commit_help}'], cwd=self.source_filepath,
                                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    commit_git_return_code = commit_git.wait()
                    if commit_git_return_code is None or commit_git_return_code != 0:
                        logger.error("==========git commit失败==========")
                    else:
                        # git push origin master
                        push_git = subprocess.Popen(['git', 'push', 'origin', 'master'], cwd=self.source_filepath,
                                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        push_git_return_code = push_git.wait()
                        if push_git_return_code is None or push_git_return_code != 0:
                            logger.error("==========git push失败==========")
                        else:
                            logger.info("==========代码提交成功==========")
                break
            else:
                confirm_attempts += 1
                remaining_attempts = self.MAX_ATTEMPTS - confirm_attempts
                if confirm_attempts < self.MAX_ATTEMPTS:
                    logger.info(f"==========请授权提交代码，防止冲突！，还剩 {remaining_attempts} 次确认==========")
                else:
                    logger.info("==========未授权提交代码，注意！！！==========")

    def deploy_server(self):
        """
        是否部署到服务器
        :return:
        """
        confirm_attempts = 0
        while confirm_attempts < self.MAX_ATTEMPTS:
            deploy_status = self.get_user_input("是否部署到服务器：（y，yes）:")
            if deploy_status in ["y", "yes"]:
                # 部署
                g = subprocess.Popen(['hexo', 'g'], cwd=self.source_filepath, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                g_return_code = g.wait()
                # 超时和执行失败时给予警告
                if g_return_code is None or g_return_code != 0:
                    logger.error("==========hexo g失败==========")
                else:
                    d = subprocess.Popen(['hexo', 'd'], cwd=self.source_filepath, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL)
                    d_return_code = d.wait()
                    if d_return_code is None or d_return_code != 0:
                        logger.error("==========hexo d失败==========")
                    else:
                        logger.info("==========部署成功==========")
                        self.git_commit("部署编译内容")
                break
            else:
                confirm_attempts += 1
                remaining_attempts = self.MAX_ATTEMPTS - confirm_attempts
                if confirm_attempts < self.MAX_ATTEMPTS:
                    logger.info(f"==========请授权部署，还剩 {remaining_attempts} 次确认==========")
                else:
                    logger.info("==========未授权部署==========")

# 迁移服务器
