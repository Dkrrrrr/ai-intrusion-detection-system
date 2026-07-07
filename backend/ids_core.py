import os
import json
import joblib
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage

from agent_core import (
    retrieve_similar_incidents_milvus,
    format_rag_context,
    add_incident_to_milvus,
    get_rag_stats
)
load_dotenv()


class IDSCore:
    def __init__(self, model_dir: str = None):
        if model_dir is None:
            base_dir = Path(__file__).parent.parent
            model_dir = base_dir / "models"
        self.model_dir = Path(model_dir)

        self.model = None
        self.scaler = None
        self.label_encoder = None
        self.selected_features = None
        self.agent = None

        self.stats = {
            "predict_count": 0,
            "attack_count": 0,
            "agent_decisions": []   # 存储最近决策记录，用于上下文工程
        }

        self._load_models()

    def _load_models(self):
        try:
            self.model = joblib.load(self.model_dir / "rf_model.joblib")
            self.scaler = joblib.load(self.model_dir / "scaler.joblib")
            self.label_encoder = joblib.load(self.model_dir / "label_encoder.joblib")
            with open(self.model_dir / "selected_features.json", "r") as f:
                self.selected_features = json.load(f)
            print(f"[IDSCore] 模型加载成功，特征数: {len(self.selected_features)}")
        except Exception as e:
            print(f"[IDSCore] 模型加载失败: {e}")

    def predict(self, features: list):
        if self.model is None:
            raise RuntimeError("模型未加载")

        self.stats["predict_count"] += 1
        x = np.array(features).reshape(1, -1)
        x_scaled = self.scaler.transform(x)

        pred_id = self.model.predict(x_scaled)[0]
        proba = self.model.predict_proba(x_scaled)[0].tolist()

        label = self.label_encoder.inverse_transform([pred_id])[0]
        classes = self.label_encoder.classes_.tolist()
        probability_dict = {cls: proba[i] for i, cls in enumerate(classes)}

        if label == "attack":
            self.stats["attack_count"] += 1

        return {
            "prediction": label,
            "probability": probability_dict
        }

    def agent_decide(self, attack_type: str, src_ip: str, risk_level: str = "高"):
        """
        Agent 决策入口（集成 Milvus RAG 知识库）
        """
        if self.agent is None:
            from agent_core import create_agent
            self.agent = create_agent()

        # ============================================================
        # 1. RAG 检索：获取历史相似案例（使用 Milvus）
        # ============================================================
        try:
            # 用攻击类型作为检索查询
            similar_cases = retrieve_similar_incidents_milvus(attack_type, k=2)
            rag_context = format_rag_context(similar_cases)
        except Exception as e:
            print(f"[RAG] 检索异常，使用默认上下文: {e}")
            rag_context = "【历史相似案例参考】\n无相似历史案例。"

        # ============================================================
        # 2. 上下文工程：近期处置记录
        # ============================================================
        recent_actions = self.stats["agent_decisions"][:5]
        if recent_actions:
            context_summary = "\n".join([
                f"- {d['attack']} from {d['ip']} → {d['action']}"
                for d in recent_actions
            ])
            context_section = f"\n\n【近期处置记录】\n{context_summary}\n请避免对同一个IP重复执行相同动作。"
        else:
            context_section = "\n\n【近期处置记录】\n暂无记录。"

        # ============================================================
        # 3. 组装系统提示词（含 RAG + 上下文工程）
        # ============================================================
        system_prompt = f"""你是一个专业的网络安全响应专家。你有以下工具：

    1. check_ip_reputation —— 查询IP的威胁情报（优先使用）
    2. check_domain_reputation —— 查询域名或URL的威胁情报
    3. block_ip —— 封禁IP（真实执行Windows防火墙规则）
    4. rate_limit_ip —— 限速IP（模拟）
    5. log_alert_only —— 仅记录

    【工作流规则】
    当你收到一个攻击告警时：
    - 如果攻击类型包含 domain 或 malware，或者源IP看起来像域名，先调用 check_domain_reputation
    - 否则先调用 check_ip_reputation

    然后根据风险评分决策：
    - 评分 > 80% 或 恶意检测 > 0 → 调用 block_ip
    - 评分 30%-80% 或 可疑检测 > 0 → 调用 rate_limit_ip
    - 评分 < 30% 且 无恶意检测 → 调用 log_alert_only

    {rag_context}
    {context_section}

    严格按照规则执行，不要跳过查询步骤。"""

        # 根据 attack_type 构建用户消息
        if "domain" in attack_type.lower() or "malware" in attack_type.lower():
            user_message = f"攻击类型：{attack_type}，域名：{src_ip}，风险等级：{risk_level}。请调用 check_domain_reputation 查询该域名的威胁情报。"
        else:
            user_message = f"攻击类型：{attack_type}，源IP：{src_ip}，风险等级：{risk_level}。"

        # 调用 Agent
        from langchain_core.messages import HumanMessage
        result = self.agent.invoke({
            "messages": [
                HumanMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]
        })

        output = result["messages"][-1].content
        if not output or output.strip() == "":
            for msg in reversed(result["messages"]):
                if hasattr(msg, "content") and msg.content and msg.content.strip():
                    output = msg.content
                    break

        # 解析动作
        if "block_ip" in output or "封禁" in output:
            action = "block_ip"
        elif "rate_limit_ip" in output or "限速" in output:
            action = "rate_limit_ip"
        else:
            action = "log_alert_only"

        # 短期记忆升级（60秒窗口）
        from agent_core import short_memory, store_incident
        upgraded = short_memory.upgrade_action(src_ip, action)
        if upgraded != action:
            action = upgraded
        short_memory.update(src_ip, action)

        # 存入长期记忆（文本存储）
        store_incident(attack_type, risk_level, action, output)

        # ============================================================
        # 4. 存入 Milvus 向量数据库（让未来能检索到这次案例）
        # ============================================================
        try:
            add_incident_to_milvus(attack_type, action, output)
        except Exception as e:
            print(f"[RAG] 存入向量库失败（不影响主流程）: {e}")

        # 记录统计
        self.stats["agent_decisions"].insert(0, {
            "attack": attack_type,
            "ip": src_ip,
            "action": action,
            "risk": risk_level
        })
        self.stats["agent_decisions"] = self.stats["agent_decisions"][:20]

        return {
            "action": action,
            "full_response": output
        }

    def agent_explain(self, attack_type: str, features: dict):
        """
        攻击解释（简化版）
        """
        return f"攻击类型 {attack_type} 可能导致数据泄露或服务中断。建议立即封禁源IP并检查日志。"

    def get_stats(self):
        return {
            "total_predictions": self.stats["predict_count"],
            "total_attacks_detected": self.stats["attack_count"],
            "recent_decisions": self.stats["agent_decisions"][:10]
        }