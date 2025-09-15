#!/bin/bash
set -e

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 检查 python3
if ! command -v python3 >/dev/null 2>&1; then
    echo "错误: 未找到 python3，请先执行：sudo apt install -y python3 python3-venv python3-pip"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "正在创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
. venv/bin/activate

# 安装依赖（如果有 requirements.txt）
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip >/dev/null
    pip install -r requirements.txt >/dev/null
fi

# 从标准输入读取 JSON 数据并传给 Python 脚本
cat - | venv/bin/python src/add_pending_record.py

# 退出虚拟环境
deactivate

echo "完成"
:wq