# AI Dev Launcher v2.0 项目介绍

AI Dev Launcher 是面向 Windows 的一体化 AI 开发工作台。用户可以在一个桌面应用中创建和管理项目、与 Codex 对话、查看执行过程、检查文件与 Git 改动、运行 PowerShell，并查看 Headroom Token 节省统计。

## 核心能力

- 通过“项目名称 + 保存位置”创建并自动初始化新项目。
- 在应用内与 Codex 流式对话，支持停止、追问和项目独立会话。
- 标准模式默认限制在当前项目；完全访问模式显示明显风险提示。
- 文件树、文本预览、Git Diff、接受和撤销改动。
- 集成 PowerShell，显示输出、错误和退出码。
- Headroom 状态、版本及 Token 节省统计。
- 启动器私有 Codex CLI 和 Headroom 自动更新，验证失败自动保留旧版本。

## 最重要的隔离原则

Codex 桌面端与 AI Dev Launcher 相互独立：

- 启动器不修改 Codex 桌面端的永久模型路由。
- 不写系统级代理或全局 Codex 配置。
- Headroom 仅包装启动器创建的 Codex 子进程，并使用 `--no-mcp` 禁止注册全局 MCP。
- 启动器关闭、崩溃或卸载后，Codex 桌面端仍可独立使用。
- 自动更新只管理启动器私有工具目录，不更新用户的全局 Codex CLI。

## 技术架构

```text
Electron 主进程
├─ Vue 3 Fluent 工作台
├─ 安全 preload / IPC
├─ Codex JSONL 会话管理
└─ Python JSON Bridge
   ├─ 项目创建与初始化
   ├─ 隔离运行环境和自动恢复
   ├─ 私有工具更新与回滚
   ├─ 文件、Git 与 PowerShell 服务
   └─ Headroom 统计读取
```

旧版 `%LOCALAPPDATA%\AI Dev Launcher\config.json` 项目配置会被直接兼容读取，无需用户迁移操作。
