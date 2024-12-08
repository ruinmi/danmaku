#!/bin/bash

# 设置工作目录为脚本所在目录
cd "$(dirname "$0")"

# 检查是否已经在运行
if [ -f "run.pid" ]; then
    pid=$(cat run.pid)
    if ps -p $pid > /dev/null 2>&1; then
        echo "程序已经在运行中 (PID: $pid)"
        exit 1
    else
        # 清理过期的 PID 文件
        rm run.pid
    fi
fi

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

# 检查配置文件中是否有账号
if ! grep -q "csrf:" config/config.yaml || ! grep -q "sessdata:" config/config.yaml; then
    echo "错误: 未找到账号配置，请先运行 ./login.sh 添加账号"
    exit 1
fi

echo "正在启动程序..."
# 创建临时日志文件
temp_log=$(mktemp)
nohup python3 src/main.py > "$temp_log" 2>&1 &
pid=$!
echo $pid > run.pid

# 等待几秒检查程序是否正常启动
sleep 2
if ! ps -p $pid > /dev/null 2>&1; then
    echo "程序启动失败！错误信息:"
    cat "$temp_log"
    rm -f run.pid "$temp_log"
    exit 1
fi

# 程序正常启动，将临时日志内容追加到正式日志文件
rm -f "$temp_log"

echo "程序已启动 (PID: $pid)"
echo "日志文件: bilibili.log" 