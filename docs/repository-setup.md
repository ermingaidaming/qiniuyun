# 仓库创建与 PR 流程

## 关键原则

先确认官方所选批次的开始时间和截止时间。只有确认已经进入开发周期后，才创建远端仓库并生成首个 commit。

当前本地仓库已经初始化，但还没有 commit。这样可以避免首个 commit 时间早于官方批次开始时间。

## 开题后首个 commit

在官方批次开始后执行：

```powershell
git add .
git commit -m "chore: initialize contest repository scaffold"
```

创建 GitHub 或 Gitee 远端仓库后执行：

```powershell
git remote add origin <your-repository-url>
git push -u origin main
```

建议远端仓库先设为私有，按比赛要求在提交截止后或评审前改为公开可访问。

## 每个功能的 PR 流程

```powershell
git switch main
git pull
git switch -c feature/<short-feature-name>
```

完成单一功能后：

```powershell
git add .
git commit -m "feat: add <feature summary>"
git push -u origin feature/<short-feature-name>
```

然后在 GitHub/Gitee 创建 PR，并完整填写模板：

- 功能描述
- 实现思路
- 测试方式
- 依赖与原创说明
- 截图或录屏

合并后回到主分支：

```powershell
git switch main
git pull
```

## 多人协作要求

- 每位队员使用自己的平台账号提交 commit。
- 每个 PR 描述中写清楚本 PR 负责的功能和实现者。
- 不要由一个人代提交全部代码。
- 如果某位队员主要负责文档、测试、视频，也应通过独立 PR 体现贡献。

## 截止前检查

- `main` 分支可以按 README 成功启动。
- 所有 PR 描述非空且与代码变更一致。
- README 列明全部依赖和原创范围。
- Demo 视频链接可访问、可播放。
- 远端仓库可公开访问。
- 没有把截止后 commit 合入参赛分支。
