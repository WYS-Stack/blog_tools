import json
import os
import re
import subprocess
import sys
import urllib.parse
from functools import partial
from pathlib import Path

from logger import logger


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

        self.config_data = self.read_config(self.config_filepath)
        self.f_Unexecuted = self.config_data["Unexecuted_files"]

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

    def read_config(self, config_filepath):
        """
        读取背景配置
        """
        with open(config_filepath, 'r', encoding="utf-8") as file:
            return json.load(file)

    def write_config(self, config_filepath, key, value, categories=None):
        """
        写入背景配置
        """
        if key == "cover":
            self.config_data[key][f"{categories}"] = f"{value}"
        elif key == "Unexecuted_files":
            self.config_data[key].append(f"{value}")
        with open(config_filepath, 'w', encoding="utf-8") as f:
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
        self.replaced_info["replaced_fail_num"] = self.replaced_info.get("replaced_fail_num", [])  # 替换失败数
        self.replaced_info["replaced_fail_info"] = self.replaced_info.get("replaced_fail_info", {})  # 替换失败原因

        # 获取图片链接
        self.link = match_url.group()
        # 记录需替换的行数
        self.replaced_info["replaced_line_number"].append(self.line_number)
        if self.link is not None:
            img_name = self.link.split("/")[-1]
            # 使用正则表达式检查是否符合URL编码的格式
            pattern = r'%[0-9a-fA-F]{2}'  # 匹配"%xx"形式的编码
            imgname_encoding_flag = re.search(pattern, img_name) is not None
            if imgname_encoding_flag:
                # 使用urllib.parse.unquote()方法进行解码
                img_name = urllib.parse.unquote(img_name)

            # 如果不是分类背景图链接
            if self.link not in self.config_data["cover"].values() and img_name.split(".")[0] not in self.config_data["cover"]:
                img_file_catalogue = file.replace(self.filepath, self.download_img_path) + "/"
                self.local_imgpath = img_file_catalogue + img_name
            # 如果是分类背景图链接
            else:
                self.local_imgpath = self.img_categorie_path + img_name

            # 路径正确 则 代表替换成功
            if os.path.exists(self.local_imgpath):
                if self.link == self.local_imgpath:
                    return self.link
                # 记录替换成功的行数
                self.replaced_info["replaced_line_success_number"].append(self.line_number)
                logger.info(f"第{self.line_number}行替换成功")
                logger.info(f"原始：{self.link}")
                logger.info(f"现在：{self.local_imgpath}")
                return self.local_imgpath
            else:
                self.replaced_info["replaced_fail_num"].append(self.line_number)
                self.replaced_info["replaced_fail_info"][f"第{self.line_number}行"] = f"图片路径错误"
                return self.link

    def Batch_replace_img_local(self):
        """
        批量替换图片链接为 本地路径
        """
        self.git_commit()
        pattern = r"https://\S*\.(?:jpg|png|jpeg)|/Users/wanghan/.*\.(jpg|png|jpeg)"
        for file in self.file_list:
            with open(file, 'r+') as f:
                lines = f.readlines()
                result = ""  # 记录修改结果
                match_url_num = 0  # 记录符合规则的URL
                self.line_number = 1  # 记录行号
                self.replaced_info = {}
                logger.info(f"===================={file}==========")
                # 对匹配到的结果进行处理并替换 为本地路径
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

                    log_message = f"检测URL总数：{match_url_num}个"
                    if self.replaced_info.get('replaced_line_number'):
                        log_message += f"，所在行数：{','.join(str(line_number) for line_number in self.replaced_info['replaced_line_number'])}"
                    if self.replaced_info.get('replaced_line_success_number'):
                        log_message += f"，修改行数：{','.join(str(line_number) for line_number in self.replaced_info['replaced_line_success_number'])}。"
                    else:
                        log_message += "，无需修改。"
                    if self.replaced_info.get('replaced_fail_num'):
                        log_message += f"失败行数：{','.join(str(line_number) for line_number in self.replaced_info['replaced_fail_num'])}。"
                    if self.replaced_info.get('replaced_fail_info'):
                        log_message += f"，失败原因：{self.replaced_info['replaced_fail_info']}。"
                    logger.info(log_message)

        self.git_commit("统一图片地址")
        self.deploy_server()

def main():
    logger.info("==========开始执行==========")
    bt = Blog_Batch_Replace_Tool()
    bt.Batch_replace_img_local()
    logger.info("==========执行结束==========")


if __name__ == '__main__':
    # Hexo博客目录
    filepath = "/Users/wanghan/Desktop/code/blog/source/_posts/"
    # 分类图片目录
    img_categorie_path = "/Users/wanghan/Desktop/code/project_test/blog_tools/blog_auto/img/"
    # 博客内含图片下载目录
    download_img_path = "/Users/wanghan/Desktop/图片/blog/"

    # 测试使用

    # filepath = "../test/"
    # img_categorie_path = "/Users/wanghan/Desktop/code/project_test/blog_tools/blog_auto/img/"
    # download_img_path = "/Users/wanghan/Desktop/code/project_test/blog_tools/img/"

    main()
