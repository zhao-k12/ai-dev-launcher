# AI Dev Launcher 2.2.1

- 修复 Codex CLI 0.146 在续聊时拒绝 `--sandbox` 参数的问题。
- 标准模式续聊改用 `sandbox_mode="workspace-write"` 配置覆盖。
- 完全访问模式续聊继续使用 Codex `resume` 原生支持的免审批参数。
- 续聊图片参数统一放到会话编号之前，符合当前 CLI 参数结构。
