---
title: conda命令
categories: conda
tags: conda
cover: 'https://images.cherain-wh.cloud/conda.png'
abbrlink: 520ad726
date: 2022-03-29 16:32:57
---
conda list



#### 创建虚拟环境

conda create -n py36tf1 numpy pandas python=3.6



#### 激活新虚拟环境命令（*表示当前所在的环境）

conda activate py36tf1

source activate py36tf1（上一步报错执行这个）



#### 查看当前环境所有包

conda list



#### 退出当前虚拟环境

conda deactivate



#### 删除虚拟环境

conda remove -n 环境名称 --all

报错时：conda env remove -n 环境名称



#### 删除虚拟环境中的包

conda remove -n 环境名称 $package_name（包名）



#### 安装离线包（tar.bz2）

conda install --use-local 离线包路径



#### 导出已有环境

conda env export > 虚拟环境名（自定义）.yaml



#### 导入环境（yaml）

conda env create -f 文件名.yaml（导入进去后文件名就是虚拟环境名）



#### 安装requirements.txt

conda install --yes --file requirements.txt



#### 在conda找不到依赖包时用pip代替安装

while read requirement; do conda install --yes $requirement || pip install $requirement; done < requirements.txt



#### 配置国内镜像源

```text
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

pip config list  # 查看配置信息
```

