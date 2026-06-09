# AI-NIDS：智能入侵检测与自动化响应系统

基于**随机森林**与**LangGraph Agent**的入侵检测系统，提供实时流量预测、AI 决策与自然语言解释，并配有 React 前端控制台。

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue)](https://reactjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-purple)](https://langchain-ai.github.io/langgraph/)

---

## ✨ 核心亮点

- 🤖 **AI Agent 自动响应**：基于 LangGraph 构建 ReAct Agent，集成 `block_ip` / `rate_limit_ip` / `log_alert_only` 三个工具，根据攻击类型、源 IP 和风险等级自动选择处置动作。
- 🧠 **短期记忆升级**：同一 IP 在 60 秒内重复攻击，动作自动升级（仅记录 → 限速 → 封禁），模拟真实安全运营的“阶梯式响应”。
- 📊 **传统机器学习检测**：随机森林（可切换 SVM/决策树）集成特征选择与 SMOTE 过采样，分类准确率 95%+。
- 🌐 **前后端分离架构**：FastAPI 提供 4 个 REST API，React + Vite 实现现代 Web 控制台，支持跨域调用。
- 📝 **LLM 智能解释**：通过兼容 OpenAI 协议的 API（如七牛云、DeepSeek）调用大模型，Prompt 工程强制输出结构化解释（危害；建议一；建议二）。
- 📄 **日志分析工具**（可选）：上传 Web 日志，AI 自动提取可疑条目并输出 JSON 格式安全报告。
- 🖥️ **遗留桌面版 GUI**：项目最初版本提供完整 Tkinter 界面（位于 `legacy/`），包含训练、评估、实时监控等功能，可作为备用或学习参考。

---

## 🛠️ 技术栈

| 层次 | 技术 |
|------|------|
| **后端框架** | FastAPI + Uvicorn |
| **AI Agent** | LangGraph, LangChain, OpenAI API 兼容接口 |
| **机器学习** | scikit-learn, imbalanced-learn, pandas, numpy |
| **前端** | React 18, Vite, Axios |
| **数据可视化** | Matplotlib, Seaborn |
| **环境管理** | python-dotenv |

---

## 📦 快速开始

### 1. 克隆仓库
```bash
git clone https://github.com/Dkrrrrr/ai-intrusion-detection-system.git
cd ai-intrusion-detection-system
```

### 2. 配置后端环境（Python）
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. 配置 API Key
复制环境变量模板并填入你的 LLM API Key（支持 OpenAI 兼容的接口）：
```bash
cp .env.example .env
```
编辑 `.env` 文件，修改以下内容：
```
QINIU_API_KEY=你的真实API_KEY
QINIU_BASE_URL=https://api.qnaigc.com/v1   # 根据服务商修改
MODEL_NAME=deepseek/deepseek-v4-flash      # 模型名称
```

### 4. 准备机器学习模型
项目依赖一个已训练好的随机森林模型。你可以：
- **使用预训练模型**：如果你已有 `models/rf_model.joblib` 等文件，直接放到 `models/` 目录。
- **自行训练**：使用你已有的训练代码（项目早期版本包含 Tkinter 训练界面）生成模型文件，并放入 models/ 目录。

### 5. 启动后端
```bash
uvicorn backend.api:app --reload --port 8000
```
访问 `http://localhost:8000/docs` 可查看自动生成的 Swagger API 文档。

### 6. 启动前端
打开另一个终端，执行：
```bash
cd frontend
npm install
npm run dev
```
访问 `http://localhost:5173` 打开 IDS 控制台。

---

## 🔌 API 接口说明

| 方法 | 端点 | 功能 | 请求示例 |
|------|------|------|----------|
| POST | `/predict` | 特征向量预测（正常/攻击 + 概率） | `{"features": [0.1, 0.2, ...]}` |
| POST | `/agent/decide` | Agent 决策响应动作 | `{"attack_type":"dos","src_ip":"192.168.1.1","risk_level":"高"}` |
| POST | `/agent/explain` | 生成攻击自然语言解释 | `{"attack_type":"dos","features":{"bytes":1500}}` |
| GET  | `/stats` | 获取预测次数、攻击次数、最近决策记录 | – |

详细参数与响应格式请查阅 Swagger 文档。

---

## 📁 项目目录结构

```
ai-intrusion-detection-system/
├── backend/               # FastAPI 后端
│   ├── api.py             # API 路由与 CORS
│   ├── ids_core.py        # 模型预测、Agent 决策、统计
│   └── agent_core.py      # LangGraph Agent 定义、工具、短期记忆
├── frontend/              # React 前端（Vite）
│   ├── src/
│   │   ├── api.js         # 后端 API 调用封装
│   │   ├── App.jsx        # 主界面（四个功能卡片）
│   │   └── index.css      # 暗色主题样式
│   ├── package.json
│   └── vite.config.js
├── models/                # 训练好的模型文件（需自行生成）
│   ├── rf_model.joblib
│   ├── scaler.joblib
│   ├── label_encoder.joblib
│   └── selected_features.json
├── legacy/                # 原始 Tkinter 桌面版（参考/备用）
│   └── main_gui.py
├── logs/                  # 运行日志（自动生成）
├── .env.example           # 环境变量模板
├── .gitignore             # Git 忽略规则
├── requirements.txt       # Python 依赖
└── README.md              # 本文档
```

---

## 🧪 测试与使用

### 通过前端控制台
1. **模型预测**：输入特征向量（逗号分隔），点击“预测”查看结果和概率。
2. **Agent 决策**：填写攻击类型（如 `dos`）、源 IP 和风险等级，点击“决策”获取建议动作。
3. **AI 解释**：输入攻击类型和可选特征（JSON 格式），获得自然语言解释。
4. **统计信息**：实时显示总预测次数、攻击次数及最近决策记录。

### 通过命令行 / curl
```bash
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"features":[0,0,...,0]}'
```

---

## 🤝 贡献与反馈

欢迎提交 Issue 或 Pull Request。如果你在使用中遇到模型加载失败、API Key 无效等问题，请检查：
- 是否已训练模型并放在 `models/` 目录。
- `.env` 文件是否配置正确。
- 后端是否运行在 `8000` 端口。

---

## 📄 许可证

MIT

---

## 🙋 作者

该项目由个人开发者独立完成，用于学习 AI Agent、全栈开发与安全检测技术。欢迎联系交流（可通过 GitHub Issue）。
