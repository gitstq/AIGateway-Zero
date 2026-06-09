<div align="center">

# 🤖 AIGateway-Zero

**Lightweight AI Model Unified Gateway | 轻量级AI模型统一网关 | 輕量級AI模型統一閘道**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-orange)](.)
[![OpenAI Compatible](https://img.shields.io/badge/OpenAI-Compatible-brightgreen)](.)

[English](#english) | [简体中文](#简体中文) | [繁體中文](#繁體中文)

</div>

---

<a name="english"></a>
## 🇺🇸 English

### 🎉 Project Introduction

**AIGateway-Zero** is a lightweight, zero-dependency AI model unified gateway that aggregates multiple LLM providers (OpenAI, Anthropic, Google Gemini, and custom providers) into a single OpenAI-compatible API endpoint.

In the era of AI explosion, developers face a common pain point: each LLM provider has its own API format, authentication method, and SDK. Switching between models requires significant code modifications. AIGateway-Zero solves this problem by providing a unified OpenAI-compatible interface, allowing downstream applications to switch models with zero code changes.

**Inspiration**: Inspired by trending projects like `maximhq/bifrost` and `berriai/litellm`, AIGateway-Zero differentiates itself by being completely dependency-free, extremely lightweight, and easy to deploy.

### ✨ Core Features

- **🚀 Zero Dependencies**: Pure Python standard library implementation, no pip install required
- **🔌 Multi-Provider Support**: OpenAI, Anthropic Claude, Google Gemini, Azure, Groq, Ollama, and any OpenAI-compatible API
- **🔄 OpenAI-Compatible API**: Drop-in replacement for OpenAI API, zero code changes for existing applications
- **⚖️ 5 Load Balancing Strategies**: Round-robin, least-latency, weighted, adaptive (composite scoring), and random
- **🛡️ Content Guardrails**: Input/output length limits, keyword filtering, model allowlisting
- **⏱️ Sliding Window Rate Limiter**: Per-client rate limiting with configurable windows
- **🔄 Automatic Fallback**: Retry with alternative providers when one fails
- **📊 Real-time Metrics**: Provider health status, latency tracking, success rates, token usage
- **🔧 Flexible Configuration**: YAML, JSON, or environment variable configuration
- **🌐 CORS Support**: Built-in cross-origin support for web applications

### 🚀 Quick Start

#### Requirements
- Python 3.8+
- API keys for your LLM providers

#### Installation

```bash
# Clone the repository
git clone https://github.com/gitstq/AIGateway-Zero.git
cd AIGateway-Zero

# Create configuration file
python3 src/main.py --init-config

# Edit the configuration with your API keys
vim aigateway.yaml
```

#### Start the Server

```bash
# Using the startup script
chmod +x scripts/run.sh
./scripts/run.sh

# Or directly with Python
python3 src/main.py

# Custom port and host
python3 src/main.py -p 9090 -H 0.0.0.0
```

#### Test the API

```bash
# List available models
curl http://localhost:8080/v1/models

# Chat completion (OpenAI-compatible)
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### 📖 Detailed Usage Guide

#### Configuration File Example

```yaml
server:
  host: 0.0.0.0
  port: 8080

gateway:
  default_model: gpt-4o
  fallback_enabled: true
  retry_attempts: 3
  load_balance_strategy: adaptive

providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: sk-your-openai-key
    models: [gpt-4o, gpt-4o-mini]
    request_format: openai
    weight: 5

  anthropic:
    api_base: https://api.anthropic.com
    api_key: sk-ant-your-key
    models: [claude-3-5-sonnet-20241022]
    request_format: anthropic
    weight: 5
```

#### Environment Variables

```bash
export AIGATEWAY_HOST=0.0.0.0
export AIGATEWAY_PORT=8080
export AIGATEWAY_DEFAULT_MODEL=gpt-4o
export AIGATEWAY_LOAD_BALANCE=adaptive
export AIGATEWAY_PROVIDER_OPENAI_API_KEY=sk-your-key
```

#### Management Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/gateway/status` | GET | Gateway status and metrics |
| `/gateway/providers` | GET | Provider list with rankings |
| `/gateway/metrics` | GET | Detailed metrics and statistics |
| `/gateway/health` | GET | Health check |
| `/v1/models` | GET | List available models |
| `/v1/chat/completions` | POST | Chat completion (OpenAI-compatible) |

### 💡 Design Philosophy & Roadmap

**Design Philosophy**:
- **Simplicity First**: Zero dependencies means zero dependency conflicts
- **Standard Compatibility**: Full OpenAI API compatibility ensures seamless integration
- **Production Ready**: Built-in rate limiting, guardrails, health checks, and fallback

**Roadmap**:
- [ ] Streaming response optimization with true SSE
- [ ] Request/response caching layer
- [ ] WebSocket support for real-time applications
- [ ] Plugin system for custom middleware
- [ ] Docker containerization
- [ ] Kubernetes Helm chart

### 📦 Deployment Guide

#### Direct Deployment
```bash
python3 src/main.py -c aigateway.yaml
```

#### Background Service (Linux)
```bash
nohup python3 src/main.py > gateway.log 2>&1 &
```

#### Systemd Service
Create `/etc/systemd/system/aigateway.service`:
```ini
[Unit]
Description=AIGateway-Zero
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/AIGateway-Zero
ExecStart=/usr/bin/python3 src/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 🤝 Contributing Guide

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please follow [Conventional Commits](https://www.conventionalcommits.org/) specification.

### 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<a name="简体中文"></a>
## 🇨🇳 简体中文

### 🎉 项目介绍

**AIGateway-Zero** 是一款轻量级、零依赖的AI模型统一网关，将多个LLM提供商（OpenAI、Anthropic、Google Gemini及自定义提供商）聚合为单一的OpenAI兼容API端点。

在AI大爆发时代，开发者面临一个共同痛点：每个LLM提供商都有自己的API格式、认证方式和SDK。切换模型需要大量代码修改。AIGateway-Zero通过提供统一的OpenAI兼容接口解决这个问题，让下游应用零代码改动即可切换模型。

**灵感来源**：受 `maximhq/bifrost` 和 `berriai/litellm` 等热门项目启发，AIGateway-Zero的差异化在于完全零依赖、极致轻量、易于部署。

### ✨ 核心特性

- **🚀 零依赖**：纯Python标准库实现，无需pip安装任何包
- **🔌 多提供商支持**：OpenAI、Anthropic Claude、Google Gemini、Azure、Groq、Ollama及任何OpenAI兼容API
- **🔄 OpenAI兼容API**：即插即用替代OpenAI API，现有应用零代码改动
- **⚖️ 5种负载均衡策略**：轮询、最低延迟、加权、自适应（综合评分）和随机
- **🛡️ 内容护栏**：输入/输出长度限制、关键词过滤、模型白名单
- **⏱️ 滑动窗口限流器**：按客户端限流，支持可配置时间窗口
- **🔄 自动故障转移**：某个提供商失败时自动重试其他提供商
- **📊 实时监控指标**：提供商健康状态、延迟追踪、成功率、Token使用量
- **🔧 灵活配置**：支持YAML、JSON或环境变量配置
- **🌐 CORS支持**：内置跨域支持，方便Web应用集成

### 🚀 快速开始

#### 环境要求
- Python 3.8+
- LLM提供商的API密钥

#### 安装

```bash
# 克隆仓库
git clone https://github.com/gitstq/AIGateway-Zero.git
cd AIGateway-Zero

# 创建配置文件
python3 src/main.py --init-config

# 编辑配置文件，填入你的API密钥
vim aigateway.yaml
```

#### 启动服务

```bash
# 使用启动脚本
chmod +x scripts/run.sh
./scripts/run.sh

# 或直接用Python启动
python3 src/main.py

# 自定义端口和主机
python3 src/main.py -p 9090 -H 0.0.0.0
```

#### 测试API

```bash
# 列出可用模型
curl http://localhost:8080/v1/models

# 聊天补全（OpenAI兼容格式）
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "你好！"}]
  }'
```

### 📖 详细使用指南

#### 配置文件示例

```yaml
server:
  host: 0.0.0.0
  port: 8080

gateway:
  default_model: gpt-4o
  fallback_enabled: true
  retry_attempts: 3
  load_balance_strategy: adaptive

providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: sk-your-openai-key
    models: [gpt-4o, gpt-4o-mini]
    request_format: openai
    weight: 5

  anthropic:
    api_base: https://api.anthropic.com
    api_key: sk-ant-your-key
    models: [claude-3-5-sonnet-20241022]
    request_format: anthropic
    weight: 5
```

#### 环境变量

```bash
export AIGATEWAY_HOST=0.0.0.0
export AIGATEWAY_PORT=8080
export AIGATEWAY_DEFAULT_MODEL=gpt-4o
export AIGATEWAY_LOAD_BALANCE=adaptive
export AIGATEWAY_PROVIDER_OPENAI_API_KEY=sk-your-key
```

#### 管理端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/gateway/status` | GET | 网关状态和指标 |
| `/gateway/providers` | GET | 提供商列表及排名 |
| `/gateway/metrics` | GET | 详细指标和统计 |
| `/gateway/health` | GET | 健康检查 |
| `/v1/models` | GET | 列出可用模型 |
| `/v1/chat/completions` | POST | 聊天补全（OpenAI兼容） |

### 💡 设计思路与迭代规划

**设计理念**：
- **简洁优先**：零依赖意味着零依赖冲突
- **标准兼容**：完整的OpenAI API兼容性确保无缝集成
- **生产就绪**：内置限流、护栏、健康检查和故障转移

**迭代计划**：
- [ ] 流式响应优化，支持真正的SSE
- [ ] 请求/响应缓存层
- [ ] WebSocket支持实时应用
- [ ] 插件系统自定义中间件
- [ ] Docker容器化
- [ ] Kubernetes Helm chart

### 📦 打包与部署指南

#### 直接部署
```bash
python3 src/main.py -c aigateway.yaml
```

#### 后台服务（Linux）
```bash
nohup python3 src/main.py > gateway.log 2>&1 &
```

#### Systemd服务
创建 `/etc/systemd/system/aigateway.service`：
```ini
[Unit]
Description=AIGateway-Zero
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/AIGateway-Zero
ExecStart=/usr/bin/python3 src/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 🤝 贡献指南

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/ amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

请遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范。

### 📄 开源协议

本项目采用 MIT 协议开源 - 详见 [LICENSE](LICENSE) 文件。

---

<a name="繁體中文"></a>
## 🇹🇼 繁體中文

### 🎉 專案介紹

**AIGateway-Zero** 是一款輕量級、零依賴的AI模型統一閘道，將多個LLM提供商（OpenAI、Anthropic、Google Gemini及自定義提供商）聚合為單一的OpenAI兼容API端點。

在AI大爆發時代，開發者面臨一個共同痛點：每個LLM提供商都有自己的API格式、認證方式和SDK。切換模型需要大量程式碼修改。AIGateway-Zero透過提供統一的OpenAI兼容介面解決這個問題，讓下游應用零程式碼改動即可切換模型。

**靈感來源**：受 `maximhq/bifrost` 和 `berriai/litellm` 等熱門專案啟發，AIGateway-Zero的差異化在於完全零依賴、極致輕量、易於部署。

### ✨ 核心特性

- **🚀 零依賴**：純Python標準庫實現，無需pip安裝任何套件
- **🔌 多提供商支援**：OpenAI、Anthropic Claude、Google Gemini、Azure、Groq、Ollama及任何OpenAI兼容API
- **🔄 OpenAI兼容API**：即插即用替代OpenAI API，現有應用零程式碼改動
- **⚖️ 5種負載均衡策略**：輪詢、最低延遲、加權、自適應（綜合評分）和隨機
- **🛡️ 內容護欄**：輸入/輸出長度限制、關鍵詞過濾、模型白名單
- **⏱️ 滑動窗口限流器**：按客戶端限流，支援可配置時間窗口
- **🔄 自動故障轉移**：某個提供商失敗時自動重試其他提供商
- **📊 即時監控指標**：提供商健康狀態、延遲追蹤、成功率、Token使用量
- **🔧 靈活配置**：支援YAML、JSON或環境變數配置
- **🌐 CORS支援**：內建跨域支援，方便Web應用整合

### 🚀 快速開始

#### 環境要求
- Python 3.8+
- LLM提供商的API金鑰

#### 安裝

```bash
# 克隆倉庫
git clone https://github.com/gitstq/AIGateway-Zero.git
cd AIGateway-Zero

# 創建配置文件
python3 src/main.py --init-config

# 編輯配置文件，填入你的API金鑰
vim aigateway.yaml
```

#### 啟動服務

```bash
# 使用啟動腳本
chmod +x scripts/run.sh
./scripts/run.sh

# 或直接用Python啟動
python3 src/main.py

# 自定義埠和主機
python3 src/main.py -p 9090 -H 0.0.0.0
```

#### 測試API

```bash
# 列出可用模型
curl http://localhost:8080/v1/models

# 聊天補全（OpenAI兼容格式）
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "你好！"}]
  }'
```

### 📖 詳細使用指南

#### 配置文件範例

```yaml
server:
  host: 0.0.0.0
  port: 8080

gateway:
  default_model: gpt-4o
  fallback_enabled: true
  retry_attempts: 3
  load_balance_strategy: adaptive

providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: sk-your-openai-key
    models: [gpt-4o, gpt-4o-mini]
    request_format: openai
    weight: 5

  anthropic:
    api_base: https://api.anthropic.com
    api_key: sk-ant-your-key
    models: [claude-3-5-sonnet-20241022]
    request_format: anthropic
    weight: 5
```

#### 環境變數

```bash
export AIGATEWAY_HOST=0.0.0.0
export AIGATEWAY_PORT=8080
export AIGATEWAY_DEFAULT_MODEL=gpt-4o
export AIGATEWAY_LOAD_BALANCE=adaptive
export AIGATEWAY_PROVIDER_OPENAI_API_KEY=sk-your-key
```

#### 管理端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/gateway/status` | GET | 閘道狀態和指標 |
| `/gateway/providers` | GET | 提供商列表及排名 |
| `/gateway/metrics` | GET | 詳細指標和統計 |
| `/gateway/health` | GET | 健康檢查 |
| `/v1/models` | GET | 列出可用模型 |
| `/v1/chat/completions` | POST | 聊天補全（OpenAI兼容） |

### 💡 設計理念與迭代規劃

**設計理念**：
- **簡潔優先**：零依賴意味著零依賴衝突
- **標準兼容**：完整的OpenAI API兼容性確保無縫整合
- **生產就緒**：內建限流、護欄、健康檢查和故障轉移

**迭代計劃**：
- [ ] 流式回應優化，支援真正的SSE
- [ ] 請求/回應快取層
- [ ] WebSocket支援即時應用
- [ ] 外掛系統自定義中介軟體
- [ ] Docker容器化
- [ ] Kubernetes Helm chart

### 📦 打包與部署指南

#### 直接部署
```bash
python3 src/main.py -c aigateway.yaml
```

#### 背景服務（Linux）
```bash
nohup python3 src/main.py > gateway.log 2>&1 &
```

#### Systemd服務
創建 `/etc/systemd/system/aigateway.service`：
```ini
[Unit]
Description=AIGateway-Zero
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/AIGateway-Zero
ExecStart=/usr/bin/python3 src/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 🤝 貢獻指南

1. Fork本倉庫
2. 創建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 創建Pull Request

請遵循 [Conventional Commits](https://www.conventionalcommits.org/) 規範。

### 📄 開源協議

本專案採用 MIT 協議開源 - 詳見 [LICENSE](LICENSE) 檔案。
