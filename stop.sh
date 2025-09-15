#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -f "run.pid" ]; then
    echo "程序未运行"
    exit 0
fi

pid=$(cat run.pid)

if ! [[ "$pid" =~ ^[0-9]+$ ]]; then
    echo "无效的PID文件内容"
    rm -f run.pid
    exit 1
fi

# 检查进程是否存在
if ! kill -0 "$pid" 2>/dev/null; then
    echo "程序未运行 (PID文件过期)"
    rm -f run.pid
    exit 0
fi

echo "正在停止程序 (PID: $pid)..."
kill "$pid"

count=0
while kill -0 "$pid" 2>/dev/null; do
    sleep 1
    count=$((count + 1))
    if [ $count -ge 10 ]; then
        echo "程序未能正常停止，正在强制终止..."
        kill -9 "$pid" || true
        sleep 1
        if kill -0 "$pid" 2>/dev/null; then
            echo "错误: 无法终止程序"
            exit 1
        fi
        break
    fi
done

rm -f run.pid
echo "程序已停止"
