#!/bin/bash

# 设置工作目录为脚本所在目录
cd "$(dirname "$0")"

# 从标准输入读取JSON数据并传递给Python脚本
cat - | python3 src/add_pending_record.py

echo "完成"