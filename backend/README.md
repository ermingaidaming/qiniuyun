# Backend

当前后端是 Python 标准库实现的本地 mock API，用于保障主分支可运行。

## 运行

```powershell
python .\backend\app.py
```

## API

- `GET /api/health`：服务健康检查。
- `GET /api/session`：返回本地练习会话配置。
- `POST /api/conversation/mock`：返回 mock 口语纠错与反馈。

后续真实实现应在独立 PR 中逐步替换 mock 能力，例如 WebRTC 信令、VAD、流式 STT、LLM 编排、TTS 与抢话打断。
