# AI小说转剧本工具

面向比赛议题"基于大语言模型与实时音视频技术的下一代 AI 核心应用研发"的 AI 小说自动转剧本工具。

当前仓库是参赛项目的起步骨架，目标是先保证主分支可运行、提交记录可追踪、README 与 PR 描述符合评审规则。后续功能应通过小粒度 Pull Request 持续合入。

## 项目简介

基于大模型实现小说自动转剧本，支持小说上传、章节解析、AI 剧本生成和 Word 导出。

## 功能

- 小说上传
- 小说章节解析
- AI 剧本生成
- Word 导出

## 技术栈

### 后端

- Java 17
- Spring Boot
- MyBatis Plus

### 前端

- Vue3
- Element Plus

## 目录结构

```text
.
├── backend/                 # Spring Boot 后端服务
├── frontend/                # Vue3 前端界面
├── docs/                    # 架构、开发计划、提交清单和视频脚本
├── .github/                 # PR 模板
├── .gitignore
└── README.md
```

## 本地运行

待补充

## 依赖声明

当前版本依赖：

待补充

后续如果引入大模型 API、云服务 SDK、第三方库或素材，必须同步更新本节，并说明哪些功能为原创实现、哪些能力来自第三方库或服务。

## 原创范围

当前原创内容包括：

待补充

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
feature/novel-upload
feature/chapter-parser
feature/ai-script-generator
feature/word-export
docs/demo-video-script
```

PR 标题示例：

```text
新增小说上传功能
新增章节解析模块
接入 AI 剧本生成接口
```

## 知识产权说明

本仓库当前未声明开源许可证。除比赛规则另有约定外，作品知识产权归提交队伍所有。公开仓库前应确认不包含未经授权的第三方代码、模型权重、音视频素材、密钥或内部资料。
