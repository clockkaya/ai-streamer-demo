# AI-Streamer-Demo: 智能虚拟主播后端核心

这是一个基于 Google Gemini 大模型开发的轻量级虚拟主播后端 Demo。本项目集成了 RAG（检索增强生成）、实时 WebSocket 流式交互及 TTS（语音合成）技术，旨在模拟真实的直播间互动场景。



## 🌟 核心亮点

- **🧠 智能大脑 (LLM)**: 基于最新的 Google Gemini 2.5 系列模型，具备强大的语义理解与拟人化表达能力。
- **📚 独家记忆 (RAG)**: 利用 FAISS 向量数据库实现本地知识库检索，有效解决大模型幻觉，支持主播人设与私域知识定制。
- **⚡ 实时交互 (WebSocket)**: 采用异步 WebSocket 长连接，实现打字机式流式输出，大幅降低观众等待感。
- **🎙️ 灵动嗓音 (TTS)**: 集成微软 Edge-TTS 引擎，实现高质量语音实时合成与推送。
- **🐳 生产就绪 (Docker)**: 提供完整的 Docker 与 Docker-Compose 配置，支持一键容器化部署，屏蔽环境差异。



## 🛠️ 技术栈

- **Language**: Python 3.12
- **Framework**: FastAPI (Asynchronous IO)
- **AI/LLM**: Google GenAI SDK
- **Vector DB**: FAISS (Facebook AI Similarity Search)
- **Audio**: Edge-TTS
- **DevOps**: Docker / Docker-Compose



## 🚀 快速开始

### 1. 克隆仓库
```bash
git clone [https://github.com/your-username/ai-streamer-demo.git](https://github.com/your-username/ai-streamer-demo.git)
cd ai-streamer-demo
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件，并填入你的 API Key 及代理配置：

Ini, TOML

```
GEMINI_API_KEY=你的Gemini_API_Key
http_proxy=[http://host.docker.internal:33210](http://host.docker.internal:33210)
https_proxy=[http://host.docker.internal:33210](http://host.docker.internal:33210)
```

### 3. 使用 Docker 一键运行

Bash

```
docker-compose up -d --build
```

### 4. 访问测试

- **接口文档**: `http://localhost:8000/docs`
- **实时直播间演示**: 直接双击打开根目录下的 `test_ws.html` 即可开始互动。



## 📂 项目结构

- `app/api/`: 包含 HTTP 与 WebSocket 路由处理。
- `app/llm/`: 大模型调用逻辑与 Prompt 设计。
- `app/rag/`: 向量数据库加载与检索核心。
- `app/tts/`: 语音合成引擎。
- `data/`: 存放本地知识库文本。



## ⚠️ 免责声明

本项目仅用于技术演示与学习交流，请勿用于任何非法商业用途。请在使用前确保你拥有合法的 Google API 访问权限。