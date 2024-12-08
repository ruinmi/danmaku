#!/bin/bash

# 设置工作目录为脚本所在目录
cd "$(dirname "$0")"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3，请先安装 Python 3"
    exit 1
fi

# 检查依赖是否已安装
if [ -f "requirements.txt" ]; then
    # 检查是否已安装所有依赖
    if ! python3 -c "import qrcode, requests, yaml" 2>/dev/null; then
        echo "正在安装依赖..."
        pip3 install -r requirements.txt
    fi
fi

# 运行登录脚本
echo "正在启动登录程序..."
python3 src/login.py

# 等待用户按任意键退出
read -n 1 -s -r -p "按任意键退出..."
echo