# 🛡️ AI-NIDS

基于 LangGraph Agent、随机森林和 Milvus RAG 的智能入侵检测与自动化响应系统。

---

## ◆ 核心功能

- **Agent 自主响应**：基于 LangGraph 构建 ReAct Agent，集成威胁情报查询、IP封禁、速率限制等工具
- **RAG 经验驱动决策**：基于 Milvus 向量数据库，Agent 决策前检索历史相似案例
- **双源威胁情报**：集成 AbuseIPDB（IP信誉）和 VirusTotal（域名检测）
- **短期记忆升级**：同一 IP 在 60 秒内重复攻击，动作自动升级（记录 → 限速 → 封禁）
- **机器学习检测**：随机森林（可切换 SVM/决策树），SMOTE 过采样，准确率 95%+
- **Web 控制台**：React + Vite + Recharts 暗色主题仪表盘

---

## ◆ 技术架构

```
┌─────────────────────────────────────────┐
│         React + Vite 前端仪表盘          │
└──────────────────┬──────────────────────┘
                   │ REST API
                   ▼
┌─────────────────────────────────────────┐
│           FastAPI 后端服务               │
├─────────────────────────────────────────┤
│         LangGraph ReAct Agent           │
│   规划 → 工具调用 → 结果整合 → 输出       │
├──────────┬──────────┬───────────────────┤
│ 威胁情报  │  RAG     │   上下文管理       │
│AbuseIPDB │ Milvus   │  短期记忆(60s)     │
│VirusTotal│ HNSW     │  近期处置记录      │
├──────────┴──────────┴───────────────────┤
│           真实执行层                     │
│       Windows 防火墙 (block_ip)          │
├─────────────────────────────────────────┤
│           模型层                         │
│     随机森林 / SVM / 决策树              │
└─────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 |
| :--- | :--- |
| Agent 框架 | LangGraph |
| 向量数据库 | Milvus Lite (HNSW) |
| 嵌入模型 | Sentence-Transformers (all-MiniLM-L6-v2) |
| 威胁情报 | AbuseIPDB + VirusTotal |
| 机器学习 | scikit-learn + imbalanced-learn (SMOTE) |
| 后端 | FastAPI + Uvicorn |
| 前端 | React 18 + Vite + Recharts |
| LLM | DeepSeek API (七牛云托管) |

---

## ◆ 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Windows 10/11（真实封禁依赖 Windows 防火墙）

### 后端配置

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

创建 `backend/.env` 文件：

```env
QINIU_API_KEY=你的API密钥
QINIU_BASE_URL=https://api.qnaigc.com/v1
MODEL_NAME=deepseek/deepseek-v4-flash
ABUSEIPDB_API_KEY=你的AbuseIPDB密钥
VIRUSTOTAL_API_KEY=你的VirusTotal密钥
```

将训练好的模型文件放入 `models/` 目录：

- `rf_model.joblib`
- `scaler.joblib`
- `label_encoder.joblib`
- `selected_features.json`

启动后端：

```bash
uvicorn api:app --reload --port 8000
```

访问 `http://localhost:8000/docs` 查看 API 文档。

### 前端配置

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173` 打开控制台。

---

## ◆ API 接口

| 方法 | 端点 | 功能 |
| :--- | :--- | :--- |
| POST | `/predict` | 特征向量预测 |
| POST | `/agent/decide` | Agent 决策 |
| POST | `/agent/explain` | 攻击解释 |
| GET | `/stats` | 统计信息 |
| GET | `/rag/stats` | RAG 知识库统计 |

---

## ◆ 测试用例

| 编号 | 场景 | 输入 | 预期结果 |
| :--- | :--- | :--- | :--- |
| TC-01 | 普通IP检测 | port_scan, 45.33.22.11 | 威胁评分低 → 仅记录 |
| TC-02 | 恶意域名检测 | malware_domain, winactivate.net | 检测到恶意 → 封禁 |
| TC-03 | 重复攻击升级 | 60秒内发2次相同请求 | 第1次记录，第2次限速 |
| TC-04 | RAG检索 | 先发TC-01，再发同类请求 | 系统提示词含历史案例 |
| TC-05 | 真实封禁 | brute_force, 任意IP | Windows防火墙规则生效 |

---

## ◆ 项目结构

```
IDS/
├── backend/
│   ├── api.py              # FastAPI 入口
│   ├── ids_core.py         # 核心业务逻辑
│   └── agent_core.py       # Agent + 工具 + RAG + 记忆
├── frontend/
│   └── src/
│       ├── App.jsx         # 仪表盘主界面
│       ├── api.js          # API 调用封装
│       └── index.css       # 样式
├── models/                 # 模型文件
├── legacy/                 # 原始 Tkinter 版本
├── logs/                   # 运行日志
└── requirements.txt
```

---

## License

MIT