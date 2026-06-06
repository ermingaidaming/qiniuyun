# 持续交付计划

以下计划用于形成持续的 PR 与 commit 记录。实际排期应按官方批次开始和截止日期调整。

## 阶段 0：项目身份统一

- 统一 README、文档与 CLAUDE.md 的项目描述和技术栈。
- 确保所有文档描述同一套 AI 小说转剧本架构。

建议 PR：

- `docs: 统一项目文档与架构描述`

## 阶段 1：后端脚手架（FastAPI + Poetry）

- 初始化 Poetry 项目（pyproject.toml）。
- 搭建 FastAPI 最小骨架（health check + CORS）。
- 定义核心 Pydantic 数据模型。
- 编写首个测试。

建议 PR：

- `feat: 初始化 FastAPI 后端骨架`
- `feat: 定义核心数据模型（Novel/Chapter/Screenplay）`

## 阶段 2：前端脚手架（Next.js + TypeScript + TailwindCSS）

- 初始化 Next.js 项目。
- 搭建根布局与首页。
- 封装 API 客户端。
- 定义前端类型。

建议 PR：

- `feat: 初始化 Next.js 前端项目骨架`
- `feat: 新增 API 客户端与类型定义`

## 阶段 3：基础功能——小说管理

- 小说上传 API（TXT/EPUB）。
- 章节解析（自动识别章节边界）。
- 前端上传界面与章节列表。

建议 PR：

- `feat: 新增小说上传与章节解析 API`
- `feat: 新增小说管理界面`

## 阶段 4：CPC 因果情节图构建

- 事件抽取模块（从小说文本中提取事件）。
- 关系识别模块（因果/时序关系分类）。
- 贪婪循环破除算法（将事件关系转化为 DAG）。
- DAG 序列化与存储。
- 前端 DAG 可视化组件。

建议 PR：

- `feat: 实现事件抽取与关系识别`
- `feat: 实现 CPC 贪婪循环破除算法`
- `feat: 新增 DAG 因果图可视化`

## 阶段 5：R2 读者-重写器框架

- 滑动窗口分块策略（窗口大小、重叠量、触发条件）。
- 上下文拼接与 prompt 构建。
- 逐块改写引擎（小说→剧本片段）。
- 结果合并与一致性校验。
- 前端改写预览与对比界面。

建议 PR：

- `feat: 实现 R2 滑动窗口分块与调度`
- `feat: 实现 R2 逐块改写引擎`
- `feat: 新增改写预览与对比界面`

## 阶段 6：HAR 幻觉感知改进

- 向量存储初始化与文本索引。
- RAG 检索管线（查询构建 → 检索 → 排序）。
- 幻觉检测模块（事实一致性校验）。
- 自校正循环（检测→修正→再验证）。
- 前端校正审核界面。

建议 PR：

- `feat: 初始化向量数据库与文本索引`
- `feat: 实现 HAR RAG 检索与幻觉检测`
- `feat: 实现 HAR 自校正循环`
- `feat: 新增校正结果审核界面`

## 阶段 7：ScreenYAML 生成与导出

- ScreenYAML Schema 定义（Draft 2026-01）。
- 剧本内容映射（动作、角色、对话、括号）。
- UUID 生成与角色关系验证。
- Word/PDF 导出。
- 前端剧本预览与导出界面。

建议 PR：

- `feat: 定义 ScreenYAML Schema 与校验`
- `feat: 实现 ScreenYAML 结构化生成`
- `feat: 新增剧本预览与导出界面`

## 阶段 8：评审材料

- README 补齐依赖、原创说明、部署方式。
- 录制 Demo 视频并补充链接。
- 检查所有 PR 描述和 commit 时间。
- 清理密钥、缓存、无授权素材。

建议 PR：

- `docs: 补充 Demo 视频链接与运行说明`
- `docs: 完善依赖声明和原创范围`
- `chore: 提交前清理无关文件`

## 每个 PR 的最低要求

- 只包含一个功能或一类文档改动。
- PR 描述必须包含功能描述、实现思路、测试方式。
- 合并前本地运行通过（backend: `pytest`，frontend: `npm run test && npm run build`）。
- README 中同步新增第三方依赖。
- 若复用旧代码，PR 描述写明来源。
