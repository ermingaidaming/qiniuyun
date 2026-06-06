# SpeakFlow Coach

面向比赛议题“基于大语言模型与实时音视频技术的下一代 AI 核心应用研发”的实时 AI 英语口语陪练系统。

当前仓库是参赛项目的起步骨架，目标是先保证主分支可运行、提交记录可追踪、README 与 PR 描述符合评审规则。后续功能应通过小粒度 Pull Request 持续合入。

## 项目定位

SpeakFlow Coach 面向英语口语练习场景，规划实现浏览器端实时语音采集、语音活动检测、流式转写、LLM 对话反馈、TTS 播放与抢话打断等能力。

首版仓库提供一个本地可运行的 mock demo：

- 前端：浏览器麦克风采集、音量电平、练习文本输入、AI 反馈展示。
- 后端：零第三方依赖的 Python mock API，用于保持主分支随时可运行。
- 文档：持续交付计划、提交合规清单、Demo 视频脚本、PR 模板。

## 目录结构

```text
.
├── backend/                 # 本地 mock API 与后续实时编排服务
├── frontend/                # Web 练习界面
├── docs/                    # 架构、开发计划、提交清单和视频脚本
├── .github/                 # PR 模板
├── .gitignore
└── README.md
```

## 本地运行

当前版本只需要 Python 3.10+ 和现代浏览器。

```powershell
python .\backend\app.py
```

启动后访问：

```text
http://127.0.0.1:8000
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

## 依赖声明

当前版本没有第三方运行依赖：

- 前端使用浏览器原生 Web APIs：`getUserMedia`、Web Audio API、Fetch API。
- 后端使用 Python 标准库：`http.server`、`json`、`uuid`、`pathlib`。

后续如果引入 WebRTC、STT、LLM、TTS、VAD、数据库、前端框架或云服务 SDK，必须同步更新本节，并说明哪些功能为原创实现、哪些能力来自第三方库或服务。

## 原创范围

当前原创内容包括：

- 本地 mock 口语练习流程与页面交互。
- mock 反馈生成逻辑。
- 项目架构、开发计划、提交合规文档和 Demo 视频脚本。

如复用队员过往代码片段，必须在对应 PR 描述中写明来源、文件路径和改动范围。

## Demo 视频

Demo 视频链接待补充。提交前需要上传到可访问平台，并将链接替换到这里：

```text
TODO: https://example.com/demo-video
```

视频应包含声音讲解，覆盖核心模块、运行方式、主要功能和效果。

## 持续交付约定

- 远端仓库必须在官方开题后创建。
- 所有 commit 时间戳必须落在所选批次的开始与截止时间之内。
- 禁止最后一天一次性导入所有代码。
- 每个 PR 只做一件事，标题和描述必须与实际代码变更一致。
- PR 描述必须包含功能描述、实现思路、测试方式。
- 合并后 `main` 分支必须保持可运行。
- 多人组队时，每位队员使用自己的 GitHub/Gitee 账号提交 commit。

详细检查项见 [docs/submission-checklist.md](docs/submission-checklist.md)，远端仓库创建与 PR 流程见 [docs/repository-setup.md](docs/repository-setup.md)。

## 推荐分支与 PR 命名

```text
feature/frontend-mic-level
feature/backend-session-api
feature/vad-pipeline
feature/llm-feedback
docs/demo-video-script
```

PR 标题示例：

```text
新增浏览器麦克风音量检测界面
新增本地口语反馈 mock API
接入实时语音活动检测模块
```

## 知识产权说明

本仓库当前未声明开源许可证。除比赛规则另有约定外，作品知识产权归提交队伍所有。公开仓库前应确认不包含未经授权的第三方代码、模型权重、音视频素材、密钥或内部资料。
