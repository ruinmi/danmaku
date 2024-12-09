# B站录播弹幕自动发送工具

一个基于 Biliup 的 B站录播弹幕自动发送工具,支持多账号管理和智能弹幕发送。

## ✨ 主要功能

- 🔑 多账号管理
  - 扫码快速登录
  - Cookie 自动续期
  - 实时状态监控
- 📺 视频监控
  - 自动检测 UP 主新视频
  - 支持关键词匹配
  - 定时轮询更新
- 💬 弹幕发送
  - 支持 XML 弹幕导入
  - 智能去重过滤
  - 自动调节发送频率
  - 多账号均衡发送
- ⚡️ 高度可配置
  - 自定义发送间隔
  - 弹幕数量限制
  - 重试机制

## 🚀 快速开始

1. 给脚本添加执行权限 
    ```bash
    chmod +x start.sh login.sh add_pending_record.sh
    ```
2. 修改 `config/config.yaml`,配置需要监控的 UP 主 ID
3. 执行 `.\login.sh` 添加弹幕发送账号
4. 运行 `.\start.sh` 启动监控服务

## ⚠️ 使用须知

- 需提前安装并配置 Biliup
- Biliup 配置要求:
    - **后处理**:
        - `mv {文件} {本项目}/danmaku/`
        - `rm {本项目}/danmaku/*.mp4`
    - **下载后处理**:
        - `{本项目}/add_pending_record.sh`
