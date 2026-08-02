# AI Dev Launcher 2.4.0

- 当后台上下文达到 80,000 输入 token、20 轮对话或约 320,000 字符时，在下一次发送前自动开启新的 Codex 话题。
- 自动切换只重置后台 Codex Session，界面历史记录继续保留，不提供手动切换按钮。
- 自动识别明显的已批准实施计划，要求 Codex 直接实施和验证，不再重复制定计划。
- Headroom 私有运行时使用经过 Windows 10 实测的 Python 3.12 与 ONNX Runtime 1.19.2，恢复 Kompress 深度压缩。
- 私有 Headroom 更新现在验证 ONNX 实际导入，并修复 Windows DLL 锁与 uv 启动路径问题。
- 环境状态和底部状态栏会显示 Headroom 深度压缩是否受限。
