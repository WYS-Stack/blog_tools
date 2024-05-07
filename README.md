具体内容请看如下的“文件解释”

# 目录解释

* baidu_shoulu：百度收录博客内容脚本
* blog_auto：自动完成博客文章头部添加，自动提交部署
* img：测试的md文件中的图片
* test：测试的md文件
* youdaonote-pull：有道云笔记下载

# 文件解释

baidu_shoulu目录：

- shoulu_api.py：百度收录脚本


blog_auto目录：

   - config：配置文件夹
        - config.json：背景图、不必上传的文件、忽略检查的配置文件
        - config.py：之前在有道云记录的文章时间数据
        - OCR_config.json：百度OCR配置文件
        - simhei.ttf：微软雅黑字体文件
        - upload_config.json：七牛云上传配置文件

   - img目录：
        - 全部是背景图
   - logger目录：
        - logger.py：logger日志配置文件
   - logs目录：
        - 全是日志文件
   - batch_replace_domain.py：**将博客文章中域名批量替换其他域名的脚本**
   - batch_replace_local.py：**将博客文章的域名批量替换为本地路径的脚本**
   - blog_auto_tool.py：**博客自动化脚本（自动生成文章背景图、自动补全markdown文章需要的格式开头、自动下载文章中的图片、自动提交部署）**
     - 自动化步骤如下：
     1. 生成文章背景图
     2. 扫描执行前是否有未提交文件，防止执行后无法找回原版本，如有自动提交（git工具扫描、提交）
     3. 扫描博客主目录下符合条件的md文件，过滤了配置里的需要忽略的文件、不必执行文件（非md文件）
     4. 扫描背景图（也就是分类图）
     5. 检测博客目录下的md是否满足markdown文章开头需求，不满足自动补全（title、categories、tags、cover、date）
     6. 下载博客内文章的所有图片到本地，存放路径按照博客目录文章的1、2、3等级目录自动生成图片的目录
     7. 部署到服务器（可选）
   - center_cover_img.py：**居中背景图脚本**
   - main.py：**博客自动化脚本 的 执行入口**


img目录：

- conda目录：conda文章中的图片（测试使用）
- MySQL目录：MySQL文章中的图片（测试使用）
- 外区目录：外区文章中的图片（测试使用）


test目录：

- conda目录：conda文章（测试使用）
- MySQL目录：MySQL文章（测试使用）
- 外区目录：外区文章（测试使用）


youdaonote-pull目录：

- pull.py：有道云笔记下载（程序执行入口）
- README.md：有道云笔记下载的脚本说明书
