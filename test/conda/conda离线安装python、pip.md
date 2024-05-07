---
title: conda离线安装python、pip
categories: conda
tags: conda
cover: 'https://images.cherain-wh.cloud/conda.png'
abbrlink: 551ead98
date: 2023-03-24 17:38:41
---
# 第一种下载方法

1. 进入[Anaconda Cloud](https://anaconda.org/anaconda/repo)搜索python

![image-20230112145543964](https://images.cherain-wh.cloud/image-20230112145543964.png)

2. Ctrl+F搜索 想要的python3.10.x的版本，并点击进去

![image-20230112145751174](https://images.cherain-wh.cloud/image-20230112145751174.png)

![image-20230112145849825](https://images.cherain-wh.cloud/image-20230112145849825.png)

3. 点击Files --> 选择Version：3.10.8 ，根据自己的系统选择合适的版本下载即可

![image-20230112150408536](https://images.cherain-wh.cloud/image-20230112150408536.png)

3. （**Python 2.7.9 + 或 Python 3.4+ 以上版本都自带 pip 工具**）安装pip 同理，搜索pip，点击进入对应的pip版本页面，点击Files，选择Version，下载即可

![image-20230112151110642](https://images.cherain-wh.cloud/image-20230112151110642.png)

# 第二种下载方法

https://repo.anaconda.com/pkgs/main/

下载原理同上

![image-20230112152309990](https://images.cherain-wh.cloud/image-20230112152309990.png)

# conda离线安装环境

## 先创建一个虚拟环境

```conda
conda create -n test
```

## 进入虚拟环境

```
source activate test
```

## 安装虚拟环境

```conda
conda install --use-local python3.10.8的本地路径
```

然后就ok了

# 解决用pip安装依赖可能出现的报错

这里借鉴的文章：https://blog.csdn.net/yuan2019035055/article/details/127078251

pip安装时报错信息：

```shell
WARNING: pip is configured with locations that require TLS/SSL, however the ssl module in Python
```

## 解决方法

在pip install xxx 之后加上参数：

```pip
-i https://pypi.tuna.tsinghua.edu.cn/simple pip -U --trusted-host pypi.tuna.tsinghua.edu.cn
```

或者

```pip
-i http://pypi.douban.com/simple/  pip -U --trusted-host pypi.douban.com
```

