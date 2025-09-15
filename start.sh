#!/bin/bash
set -e

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 检查是否已有正在运行的进程
if [ -f "run.pid" ]; then
    pid=$(cat run.pid)
    if ps -p "$pid" > /dev/null 2>&1; then
        echo "程序已经在运行中 (PID: $pid)"
        exit 1
    else
        rm -f run.pid
    fi
fi

# 检查 python3 / venv
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
    echo "检查依赖..."
    pip install --upgrade pip >/dev/null
    pip install -r requirements.txt >/dev/null
fi

# 检查配置文件
if ! grep -q "csrf:" config/config.yaml || ! grep -q "sessdata:" config/config.yaml; then
    echo "错误: 未找到账号配置，请先运行 ./login.sh 添加账号"
    exit 1
fi

echo "正在启动程序..."
temp_log=$(mktemp)
nohup venv/bin/python src/main.py > "$temp_log" 2>&1 &
pid=$!
echo $pid > run.pid

sleep 2
if ! ps -p "$pid" > /dev/null 2>&1; then
    echo "程序启动失败！错误信息："
    cat "$temp_log"
    rm -f run.pid "$temp_log"
    deactivate
    exit 1
fi

cat "$temp_log" >> bilibili.log 2>/dev/null || true
rm -f "$temp_log"

echo "程序已启动 (PID: $pid)"
echo "日志文件: bilibili.log"

# 退出虚拟环境
deactivate
