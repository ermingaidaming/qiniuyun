# 架构设计

## 当前最小闭环

```text
Browser UI
  ├─ Microphone capture and audio meter
  ├─ Practice text input
  └─ Feedback display
        │
        ▼
Python mock API
  ├─ Session config
  ├─ Mock speaking correction
  └─ Mock latency and CEFR metrics
```

这个闭环用于保证主分支从第一天起可运行，后续每个 PR 在此基础上替换或增强单一模块。

## 目标架构

```text
Client
  ├─ WebRTC audio uplink
  ├─ AI audio downlink
  └─ Realtime feedback UI
        │
        ▼
Realtime Gateway
  ├─ Signaling
  ├─ VAD chunking
  ├─ Barge-in events
  └─ Audio pacing
        │
        ▼
AI Orchestrator
  ├─ Streaming STT
  ├─ Semantic turn detection
  ├─ LLM feedback and dialogue
  ├─ Streaming TTS
  └─ Learning report
```

## 模块拆分建议

- `frontend`：实时练习界面、麦克风权限、音频电平、对话流、反馈展示。
- `backend`：会话管理、mock API、后续实时信令和 AI 编排。
- `docs`：提交计划、架构决策、Demo 视频脚本和评审材料。

## 后续真实能力接入顺序

1. 浏览器端音频采集和本地 VAD。
2. 后端会话 API 和实时事件协议。
3. 流式 STT 接口。
4. LLM 反馈与对话编排。
5. TTS 播放与抢话打断。
6. 学习报告、评分曲线和 Demo 数据。

每一步应单独建 PR，避免大功能一次性合并。
