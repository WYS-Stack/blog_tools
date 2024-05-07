import json
import os
import re
import subprocess
import sys
import urllib.parse
from functools import partial
from pathlib import Path

import qiniu
import requests
import urllib3

from logger import logger


def get_input():
    """
    获取输入的域名
    """
    # 正则表达式模式，用于匹配域名
    pattern = r'^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$'
    MAX_ATTEMPTS = 3
    update_domain = None
    input_attempts = 0

    while input_attempts < MAX_ATTEMPTS:
        if update_domain is None:
            update_domain = input("请输入更换的域名：")
            if not update_domain.strip():
                update_domain = None
                print("输入不能为空值，请重新输入第一次数据：")
                continue
            else:
                match = re.match(pattern, update_domain)
                if not match:
                    update_domain = None
                    print("域名格式错误")
        else:
            second_input = input("请再次输入更换的域名：")
            if not second_input.strip():
                print("输入不能为空值，请重新输入第二次数据：")
                continue

            if second_input == update_domain:
                return update_domain
            else:
                print("数据不一致，请重新输入。")
                update_domain = None
                input_attempts += 1

    print("验证次数已达上限，程序退出。")
    sys.exit(300)


class Blog_Batch_Replace_Tool():
    """
    向有道云导出笔记中 添加 Hexo的标题和创建时间
    """

    def __init__(self):
        # 源代码路径
        source_filepath_match = re.match(r"(.*/)source/.*$", filepath)
        self.source_filepath = source_filepath_match.group(1) if source_filepath_match else None
        self.filepath = filepath
        self.one_dirs = Path(self.filepath).iterdir()
        self.img_categorie_path = img_categorie_path
        self.download_img_path = download_img_path
        self.config_filepath = 'config/config.json'
        self.upload_config_filepath = 'config/upload_config.json'

        self.config_data = self.read_config(self.config_filepath)
        self.f_Unexecuted = self.config_data["Unexecuted_files"]
        self.upload_config_data = self.read_config(self.upload_config_filepath)

        self.MAX_ATTEMPTS = 3
        self.VALID_OPTIONS = ["y", "yes", "n", "no"]
        self.Unexecuted_file_num = 0
        self.Unexecuted_file_add = 0
        self.file_list = []

        self.blog_dirs()

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
                        self.write_config(self.config_filepath, "Unexecuted_files", onedir)
                        self.Unexecuted_file_add += 1
                    else:
                        logger.info(f"未执行文件（非md）：{onedir}")

    def read_config(self, filepath):
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

    def git_detection_not_submit(self, status):
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
                    'D ': '删除'
                }
                modified_files = []

                for file_status in result.stdout.split('\n'):
                    prefix = file_status[:2]
                    if prefix in file_changes:
                        action = file_changes[prefix]
                        file_name = file_status[2:].strip()
                        modified_files.append((action, file_name))

                for action, file_name in modified_files:
                    logger.info(f"{action}的文件：{file_name}")
        return commit_status

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
                    commit_git = subprocess.Popen(['git', 'commit', '-m', f'{git_commit_help}'],
                                                  cwd=self.source_filepath,
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
                    logger.info(f"==========请务必在更新图片地址前提交！，还剩 {remaining_attempts} 次确认==========")
                else:
                    logger.info("==========未在修改图片地址前提交代码，强制退出！！！==========")
                    if self.filepath == "../test/":
                        pass
                    else:
                        sys.exit(500)

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

    def validate_update_domain(self):
        update_domain = self.upload_config_data["七牛云"]["qiniu_domain_name"]
        pattern = r'^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$'
        match = re.match(pattern, update_domain)
        if not match:
            logger.error("域名格式错误")
            return False
        else:
            self.update_domain = update_domain
            return self.update_domain

    def upload_image_to_qiniu(self):
        """
        七牛云上传背景cover图片
        :return:
        """

        access_key = self.upload_config_data["七牛云"]["access_key"]
        secret_key = self.upload_config_data["七牛云"]["secret_key"]
        bucket = self.upload_config_data["七牛云"]["bucket"]

        q = qiniu.Auth(access_key, secret_key)

        # 先检查七牛云上是否已经存在同名的图片
        bucket_manager = qiniu.BucketManager(q)
        ret, info = bucket_manager.stat(bucket, self.img_name)
        if ret:
            url = 'https://{0}/{1}'.format(self.update_domain, self.img_name)
            logger.info(f"上传-图片-重复：{url}")
            # 如果文件已经存在，直接返回链接
            return 200, url

        # 文件不存在，进行上传
        try:
            if self.img_name_coding:
                token = q.upload_token(bucket, self.img_name_coding)
                ret, info = qiniu.put_file(token, self.img_name_coding, self.img_file_catalogue + self.img_name_coding)
            else:
                token = q.upload_token(bucket, self.img_name)
                ret, info = qiniu.put_file(token, self.img_name, self.img_file_catalogue + self.img_name)
        except FileNotFoundError:
            logger.error(f"上传-图片-失败：未找到文件，图片路径：{self.img_file_catalogue}，图片名：{self.img_name}")
            return 500, '上传失败，请重试'
        if ret:
            url = 'https://{0}/{1}'.format(self.update_domain, ret['key'])
            logger.info(f"上传-图片-链接：{url}")
            return 200, url
        else:
            logger.error(f"上传-图片-失败：请手动上传")
            return 500, '上传失败，请重试'

    def upload_and_replace_images(self):
        """
        上传后替换图片
        :param link: 图片链接
        :param update_domain: 修改的域名
        :param replaced_info: 替换详情
        :param line_number: 替换行数
        :param img_name: 图片名
        :param img_path: 图片整体路径
        :return:
        """
        # 提取图片链接的域名
        extract_domain = re.match(r'^https://([^/]+)', self.link)
        if extract_domain:
            extract_domain_name = extract_domain.group(1)
            # 记录需替换的行数
            self.replaced_info["replaced_line_number"].append(self.line_number)
            # 检查提取的域名是否为 指定域名
            if extract_domain_name != self.update_domain:
                self.replaced_info["replaced_num"].append(self.line_number)
                # 上传图片 到 新的域名
                img_upload_code, img_upload_url = self.upload_image_to_qiniu()
                if img_upload_code == 200:
                    # 记录替换成功的行数
                    self.replaced_info["replaced_line_success_number"].append(self.line_number)
                    logger.info(f"图片替换成功。原始链接：{self.link}，替换链接：{img_upload_url}")
                    # 替换域名
                    return img_upload_url
                else:
                    self.replaced_info["replaced_fail_num"].append(self.line_number)
                    self.replaced_info["replaced_fail_info"][f"第{self.line_number}行"] = "上传失败"
        return self.link

    def download_image(self, file):
        try:
            # 下载图片
            headers = {'Connection': 'close'}
            response = self.session.get(self.link, headers=headers, verify=False)
            if response.status_code == 200:
                logger.info(f"下载-图片-链接：{self.link}")
                with open(self.img_file_path, 'wb') as f:
                    f.write(response.content)
                self.replaced_info["download_num"] += 1
            else:
                self.replaced_info["error_download_num"] += 1
                logger.error(f"下载-图片-失败：{response.status_code} - {file}")
        except requests.RequestException as e:
            # 生成生成器。查看图片源路径下有没有名为"img_name"的
            search_path = Path(self.img_file_catalogue).rglob(self.img_name)
            # 在生成器中依次寻找，找到返回，否则为None
            file_in_path = next(search_path, None)
            if file_in_path:
                self.replaced_info["download_num"] += 1
                logger.info(f"下载-图片-本地迁移")
                # 移动文件位置
                file_in_path.rename(self.img_file_path)
            else:
                self.replaced_info["error_download_num"] += 1
                logger.error(f"下载-图片-发生错误：{e} - {file}")
                logger.error(f"请手动下载图片：{self.link}，至：{self.img_file_path}")

    def replace_image_domain(self, match_url, file):
        """
        替换域名
        :param match_url: 第一次匹配到的URL
        :param update_domain: 更换的域名
        :param line_number: 当前行号
        :param replaced_line_number: 记录行号
        :return:
        """
        self.replaced_info["replaced_line_number"] = self.replaced_info.get("replaced_line_number", [])  # 记录修改行号
        self.replaced_info["replaced_line_success_number"] = self.replaced_info.get("replaced_line_success_number",
                                                                                    [])  # 记录成功修改的行
        self.replaced_info["replaced_num"] = self.replaced_info.get("replaced_num", [])  # 总替换数
        self.replaced_info["replaced_fail_num"] = self.replaced_info.get("replaced_fail_num", [])  # 替换失败数
        self.replaced_info["replaced_fail_info"] = self.replaced_info.get("replaced_fail_info", {})  # 替换失败原因
        self.replaced_info["download_num"] = self.replaced_info.get("download_num", 0)  # 总下载数
        self.replaced_info["error_download_num"] = self.replaced_info.get("error_download_num", 0)  # 下载失败数

        # 获取图片链接
        self.link = match_url.group()
        if self.link is not None:
            self.img_file_catalogue = file.replace(self.filepath, self.download_img_path) + "/"
            self.img_name = self.link.split("/")[-1]
            self.img_name_coding = ""
            # 使用正则表达式检查是否符合URL编码的格式
            pattern = r'%[0-9a-fA-F]{2}'  # 匹配"%xx"形式的编码
            imgname_encoding_flag = re.search(pattern, self.img_name) is not None
            if imgname_encoding_flag:
                # 使用urllib.parse.unquote()方法进行解码
                self.img_name_coding = urllib.parse.unquote(self.img_name)
                self.img_file_path = self.img_file_catalogue + self.img_name_coding
            else:
                self.img_file_path = self.img_file_catalogue + self.img_name
            if not os.path.exists(self.img_file_catalogue):
                os.makedirs(self.img_file_catalogue)
            # 如果图片不存在且不是分类背景图
            if not os.path.exists(self.img_file_path):
                if self.link not in self.config_data["cover"].values():
                    self.download_image(file)
                    self.link = self.upload_and_replace_images()
                # 如果是分类背景图
                else:
                    self.img_name = [k for k, v in self.config_data["cover"].items() if v == self.link][0] + ".png"
                    self.link = self.upload_and_replace_images()
                    categories = file.split(self.filepath)[-1].split("/")[0]
                    self.write_config(self.config_filepath, "cover", self.link, categories)
            # 如果图片存在
            else:
                self.link = self.upload_and_replace_images()

        # 下载失败或已经是指定域名，则保持原样返回
        return self.link

    def Batch_replace_img_links(self):
        """
        批量更换图片链接（用于更换指定域名或统一所有域名时使用）
        """
        self.git_commit()
        self.validate_update_domain()
        if self.update_domain:
            pattern = r'https://\S*\.(?:jpg|png|jpeg)'
            self.session = requests.session()
            # 测试添加
            urllib3.disable_warnings()

            for file in self.file_list:
                with open(file, 'r+') as f:
                    lines = f.readlines()
                    result = ""  # 记录修改结果
                    match_url_num = 0  # 记录符合规则的URL
                    self.line_number = 1  # 记录行号
                    self.replaced_info = {}
                    logger.info(f"=========={file}==========")
                    # 对匹配到的结果进行处理并替换域名
                    for line in lines:
                        # 返回替换后的结果、检测到的URL数量
                        replaced_result, replaced_count = re.subn(pattern,
                                                                  partial(self.replace_image_domain, file=file), line)
                        result += replaced_result
                        match_url_num += replaced_count
                        self.line_number += 1  # 行号增加

                    if result:
                        # 将文件指针定位到文件开头
                        f.seek(0)
                        f.write(result)
                        # 截断文件内容到当前写入位置，防止旧内容残留
                        f.truncate()
                        logger.info(
                            f"检测URL总数：{match_url_num}个，"
                            f"所在行数：{','.join(str(line_number) for line_number in self.replaced_info['replaced_line_number']) if self.replaced_info['replaced_line_number'] else '无'}。"
                            f"需替换行数：{','.join(str(line_number) for line_number in self.replaced_info['replaced_num']) if self.replaced_info['replaced_num'] else '无'}，"
                            f"修改行数：{','.join(str(line_number) for line_number in self.replaced_info['replaced_line_success_number']) if self.replaced_info['replaced_line_success_number'] else '无'}，"
                            f"失败行数：{','.join(str(line_number) for line_number in self.replaced_info['replaced_fail_num']) if self.replaced_info['replaced_fail_num'] else '无'}。"
                            f"失败原因：{self.replaced_info['replaced_fail_info']}。"
                            f"下载图片数量：{self.replaced_info['download_num']}，"
                            f"下载失败数量：{self.replaced_info['error_download_num']}")

            self.git_commit("统一图片地址")
            self.deploy_server()


def main():
    logger.info("==========开始执行==========")
    bt = Blog_Batch_Replace_Tool()
    bt.Batch_replace_img_links()
    logger.info("==========执行结束==========")


if __name__ == '__main__':
    # Hexo博客目录
    filepath = "/Users/wanghan/Desktop/code/blog/source/_posts/"
    # 分类图片目录
    img_categorie_path = "./img/"
    # 博客内含图片下载目录
    download_img_path = "/Users/wanghan/Desktop/图片/blog/"

    # # 测试使用
    #
    # filepath = "../test/"
    # img_categorie_path = "./img/"
    # download_img_path = "../img/"

    main()
