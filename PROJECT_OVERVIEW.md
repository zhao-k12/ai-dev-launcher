# AI Dev Launcher 项目介绍

AI Dev Launcher 是一个面向 Windows 的本地 AI 开发环境启动器。它把项目管理、
环境检查、项目初始化和 Codex 启动集中到一个桌面界面中，让用户不必反复输入
PowerShell 命令。

## 它解决什么问题

使用 Codex 开发多个本地项目时，用户通常需要手动切换目录、检查工具、准备
`AGENTS.md`，再通过 Headroom 启动 Codex。AI Dev Launcher 将这些重复步骤整合为
可视化操作：

1. 注册和管理多个本地项目。
2. 自动检测 Git、Codex、Headroom 及可选 AI 工具。
3. 通过向导预览并初始化项目。
4. 自动生成或安全更新 `AGENTS.md`。
5. 一键在目标项目目录中通过 Headroom 启动 Codex。

## 核心特点

- **Windows 桌面界面**：基于 Electron、Vue 3 和 TypeScript。
- **保留 Python 核心**：CLI 和 GUI 共用项目管理、配置、检测及启动逻辑。
- **项目文件安全**：移除项目只删除注册信息，不删除项目目录。
- **初始化可预览**：先执行 dry-run，再由用户确认写入。
- **增量维护 AGENTS.md**：只管理带标记的区块，保留用户原有内容并创建备份。
- **隐私设置**：通过 Headroom 启动时关闭 telemetry 和 update check。
- **可选工具不强制安装**：jCodeMunch 与 Repomix 缺失不会阻止使用。
- **自包含安装包**：Windows 安装版内置 Python 核心，不依赖源码虚拟环境。

## 适用人群

- 希望通过图形界面使用 Codex CLI 的 Windows 用户。
- 同时维护多个代码项目的个人开发者。
- 希望统一项目初始化规范和 `AGENTS.md` 的团队。
- 已使用 Headroom，希望集中管理启动流程的用户。

## 使用流程

```text
安装启动器
   ↓
添加本地项目
   ↓
检查 Git / Codex / Headroom
   ↓
预览并初始化项目
   ↓
一键启动 Codex
```

首次在一台电脑上使用时，需要先安装 Git、Codex CLI 和 Headroom，并完成 Codex
账号授权。启动器不会复制账号凭证或个人 Skills；这些内容由每台电脑上的 Codex
用户环境单独管理。

## 技术架构

```text
Electron 主进程
   ├─ Vue 3 桌面界面
   ├─ 安全的 preload / IPC 边界
   └─ Python JSON Bridge
         ├─ 项目注册与配置
         ├─ 工具检测
         ├─ 项目初始化
         └─ Headroom / Codex 启动编排
```

配置默认保存在：

```text
%LOCALAPPDATA%\AI Dev Launcher\config.json
```

## 当前版本

当前桌面版本为 `1.0.0`，已经覆盖基础项目管理、环境检测、项目初始化向导和
Codex 一键启动。详细安装、开发和测试说明请参阅 [README.md](README.md)。

