# CRA Studio：桌面应用

[English](../studio.md) · [各平台接入](integrations.md)

CRA Studio 把整套工具打包成**一个可执行文件**：本地图形界面，加上 `cra` MCP 服务器、`cra` 命令行和 `cra-agent` 循环。它参照了开源 AI-for-science 工作台的形态：
- 打开项目；
- 接入任意模型接口；
- 由 agent 通过工具干活，你在一旁看着并审批。

代码是原创实现，专门服务于"先证伪"的密码学研究流程。

## 获取
- **直接下载**：在 GitHub Release 页面下载 `CRA-Studio-windows-x64.exe`、`CRA-Studio-macos-arm64` 或 `CRA-Studio-linux-x64`。每次打 `v*` 标签时，`release` 工作流会自动构建这三个文件。
  - 文件没有代码签名。Windows 上 SmartScreen 拦截时，点"更多信息 → 仍要运行"。
  - macOS 上先执行一次 `xattr -d com.apple.quarantine CRA-Studio-macos-arm64 && chmod +x CRA-Studio-macos-arm64`。
- **自己构建**：`pip install -e lib/core -e lib/bench -e lib/mcp -e lib/studio pyinstaller && pyinstaller packaging/cra-studio.spec --noconfirm`，产物在 `dist/` 目录。
- **从源码运行**：`pip install -e lib/studio …`，然后运行 `cra-studio`。

## 使用
启动 `CRA-Studio`，浏览器会打开 `http://127.0.0.1:8770/#t=<令牌>`。

1. **项目**：打开一个研究目录，或者新建一个（会生成黑板文件和论文骨架）。
2. **设置 → 模型接口**：
   - 选一个预设（OpenAI、DeepSeek、GLM、Kimi、通义、MiniMax、OpenRouter、Ollama、vLLM），**或者直接填任意 OpenAI 兼容的 Base URL**，再填 API key 和模型 id。点"测试连接"可以列出该接口提供的模型。
   - key 只保存在本机的用户配置文件里（权限 600），保存后不会再显示，也不会写进项目或 git。配置文件位置：Windows 为 `%APPDATA%\cra\studio.json`，macOS 为 `~/Library/Application Support/cra/studio.json`，Linux 为 `~/.config/cra/studio.json`。
   - 如果设置了环境变量 `OPENAI_BASE_URL`、`OPENAI_API_KEY`、`CRA_MODEL`，会用它们填补空着的字段。
3. **概览**：显示阶段、各状态 claim 的数量、证据行数、阶段门结果和下一步任务；点"执行"会把第一项任务交给助手。
4. **研究助手**：对话界面，模型只能通过 cra 工具操作项目。
   - 每次工具调用和返回结果都会显示出来。
   - 破坏性操作（`phase_advance`、`file_write`）会等你点**允许**或**拒绝**。
   - 每个项目的对话可以接着上一次继续；勾选"新对话"则重新开始。
   - 助手不能执行命令。需要跑实验时，它会告诉你命令，你在本地跑完后，再用日志登记证据。
5. **账本**：查看 claims 表、evidence 表和各个黑板文件。
6. **接入其他工具**：为 Claude Code、Codex、Cline、Cursor、VS Code 等 21 个平台生成 MCP 配置。可执行文件本身就是 MCP 服务器，所以生成的配置直接调用 `<CRA-Studio> mcp --project …`。

## 一个文件，多种用法
```text
CRA-Studio                                   图形界面（默认）
CRA-Studio mcp --project <目录> [--http]     cra MCP 服务器（stdio 或 Streamable HTTP）
CRA-Studio install --host <平台> --project <目录>   为指定平台写入 MCP 配置
CRA-Studio agent --model <id> --project <目录>      终端里的 agent（OpenAI 兼容接口）
CRA-Studio cra <参数>                        黑板命令行（init、status、gate、claim、evidence、check、hook）
CRA-Studio doctor --project <目录>           自检
```

## 安全
- 图形界面只监听 127.0.0.1。
- 每个 API 请求都必须带上本次启动生成的令牌（放在 URL 的 # 后面），且 Host 头必须是本机地址，所以浏览器里的其他网页无法操控它。
- 对浏览器来说，API key 只能写入，读不回来。
- 你发给助手的内容，以及助手读到的项目内容，都会发送到你配置的模型接口，请据此选择接口。
- cra 没有任何投稿、发邮件或公开发布的功能。
