import os
import json
import joblib
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

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
            "agent_decisions": []
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
        if self.agent is None:
            from .agent_core import create_agent
            self.agent = create_agent()

        from langchain_core.messages import HumanMessage
        user_message = f"""攻击类型：{attack_type}，源IP：{src_ip}，风险等级：{risk_level}。
请从以下工具中选择合适的动作：block_ip, rate_limit_ip, log_alert_only。
直接调用工具，不需要额外解释。"""

        result = self.agent.invoke({"messages": [HumanMessage(content=user_message)]})
        output = result["messages"][-1].content

        if "block_ip" in output or "封禁" in output:
            action = "block_ip"
        elif "rate_limit_ip" in output or "限速" in output:
            action = "rate_limit_ip"
        else:
            action = "log_alert_only"

        from .agent_core import short_memory, store_incident
        upgraded = short_memory.upgrade_action(src_ip, action)
        if upgraded != action:
            action = upgraded
        short_memory.update(src_ip, action)
        store_incident(attack_type, risk_level, action, "success")

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
        # 简化版解释，可接入真实 LLM
        return f"攻击类型 {attack_type} 可能导致数据泄露或服务中断。建议立即封禁源IP并检查日志。"

    def get_stats(self):
        return {
            "total_predictions": self.stats["predict_count"],
            "total_attacks_detected": self.stats["attack_count"],
            "recent_decisions": self.stats["agent_decisions"][:10]
        }