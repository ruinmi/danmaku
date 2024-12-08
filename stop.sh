#!/bin/bash

# 设置工作目录为脚本所在目录
cd "$(dirname "$0")"

# 检查PID文件是否存在
if [ ! -f "run.pid" ]; then
    echo "程序未运行"
    exit 0
fi

# 读取PID
pid=$(cat run.pid)

# 检查PID是否为数字
if ! [[ "$pid" =~ ^[0-9]+$ ]]; then
    echo "无效的PID文件内容"
    rm run.pid
    exit 1
fi

# 检查进程是否存在
if ! ps -p $pid > /dev/null 2>&1; then
    echo "程序未运行 (PID文件过期)"
    rm run.pid
    exit 0
fi

# 停止进程
echo "正在停止程序 (PID: $pid)..."
kill $pid

# 等待进程结束
count=0
while ps -p $pid > /dev/null 2>&1; do
    sleep 1
    count=$((count + 1))
    if [ $count -ge 10 ]; then
        echo "程序未能正常停止，正在强制终止..."
        kill -9 $pid
        sleep 1
        if ps -p $pid > /dev/null 2>&1; then
            echo "错误: 无法终止程序"
            exit 1
        fi
        break
    fi
done

# 删除PID文件
rm -f run.pid

echo "程序已停止" 