# AI Dev Launcher 2.2.2

- 修复 Windows 进程管道传输中文项目名称时产生 UTF-8 代理字符的问题。
- Electron 与 Python 核心之间改用 ASCII-only JSON，Unicode 内容通过标准转义无损传输。
- 新增中文项目名端到端测试，覆盖创建、初始化 `AGENTS.md` 和项目注册。
