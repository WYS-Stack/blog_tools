---
title: >-
  Mysql启动报错：Cannot boot server version 80024 on data directory built by version
  80026. Downgrade is not supported
categories: MySQL
tags: MySQL
cover: 'https://images.cherain-wh.cloud/MySQL.png'
abbrlink: '32481e13'
date: 2023-03-19 01:41:41
---



















>  环境：centos8、mysql8.0.24

记录一次这个坑，今天上服务器使用mysql，突然发现`mysql -p -uroot`连接不上还报错，加上`-h 127.0.0.1`才能连接。就很纳闷怎么会这样，报错是缺少一个/tmp/mysql.sock文件。后面看了一个日志`iZ2ze41qg0fuzjvz3491rjZ.err`，里面写的内容我直接震惊了。。。` Cannot boot server version 80024 on data directory built by version 80026. Downgrade is not supported
mysqld: Can't open file: 'mysql.ibd' (errno: 0 - )`

报错信息如下：

![image-20230319015533365](https://images.cherain-wh.cloud/image-20230319015533365.png)

我一看这不是数据目录有问题吗，而且版本还不一致。立马去看了眼数据库，然后啥都没了。。就像是刚搭建的mysql。。。无语了

然后我就开始kuchikuchi一顿查：

```shell
find / -name mysql
```

![image-20230319020024493](https://images.cherain-wh.cloud/image-20230319020024493.png)



终于经过我的深入探索，发现上面两个文件都是mysql的数据目录。。

通过查看mysql配置文件：`/etc/my.cnf`发现`/www/server/data/mysql`是我正在使用的数据目录。

<img src="https://images.cherain-wh.cloud/image-20230319020436508.png" alt="image-20230319020436508" style="zoom:50%;" />

这家伙看了一遍啥也没有啊，再看看第一个数据目录：

<img src="https://images.cherain-wh.cloud/image-20230319020535328.png" alt="image-20230319020535328" style="zoom:50%;" />

这之前建的数据库什么的都在这呢，差点以为数据不见了。虚惊一场。下面说操作（困了

1. 把数据库配置文件之前`/www/server/data/mysql`全部替换成`/var/lib/mysql`
2. `socker='/var/lib/mysql/mysql.sock'`这个你保持原样也可以，但是启动的时候报错：找不到`/tmp/mysql.sock`，那就`find / -name mysql.sock`，把找到的文件路径替换到这。
3. 启动服务`systemctl start mysql`

<img src="https://images.cherain-wh.cloud/image-20230319020844623.png" alt="image-20230319020844623" style="zoom:60%;" />

4. 我这报错了，不知道其他的会不会成。报错：`Different lower_case_table_names settings for server`

![image-20230319021735326](https://images.cherain-wh.cloud/image-20230319021735326.png)

5. 去配置文件`my.cnf`，把它注销了，再启一遍，你就会发现以前的数据又回来了。

<img src="https://images.cherain-wh.cloud/image-20230319022021365.png" alt="image-20230319022021365" style="zoom:50%;" />---
