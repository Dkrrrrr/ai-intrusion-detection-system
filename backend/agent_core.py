from dotenv import load_dotenv
load_dotenv()
import os
import time
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent

QINIU_API_KEY = os.environ.get("QINIU_API_KEY", "")
QINIU_BASE_URL = os.environ.get("QINIU_BASE_URL", "https://api.qnaigc.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek/deepseek-v4-flash")

# 工具定义
@tool
def block_ip(ip: str) -> str:
    """封禁一个IP地址，阻止其访问系统。"""
    print(f"[ACTION] 封禁 IP: {ip}")
    return f"已封禁 {ip}"

@tool
def rate_limit_ip(ip: str) -> str:
    """对某个IP地址启用速率限制。"""
    print(f"[ACTION] 对 IP {ip} 启用速率限制")
    return f"已限制 {ip} 速率"

@tool
def log_alert_only(attack_type: str, src_ip: str) -> str:
    """仅记录告警，不执行任何主动响应。"""
    print(f"[ACTION] 仅记录告警: {attack_type} from {src_ip}")
    return f"已记录 {attack_type} 攻击，源IP {src_ip}"

tools = [block_ip, rate_limit_ip, log_alert_only]

# 长期记忆（内存存储）
_long_term_memory_store = []

def store_incident(attack_type: str, risk_level: str, action: str, result: str):
    text = f"攻击类型: {attack_type}, 风险等级: {risk_level}, 决策动作: {action}, 结果: {result}"
    _long_term_memory_store.append(text)
    if len(_long_term_memory_store) > 50:
        _long_term_memory_store.pop(0)

def retrieve_similar_incidents(attack_type: str, risk_level: str, k=2):
    query_parts = []
    if attack_type:
        query_parts.append(attack_type)
    if risk_level:
        query_parts.append(risk_level)
    matched = []
    for item in _long_term_memory_store:
        if any(part in item for part in query_parts):
            matched.append(item)
    if matched:
        return "\n".join(matched[:k])
    return "无相似历史案例"

def create_agent():
    if not QINIU_API_KEY:
        raise ValueError("请设置环境变量 QINIU_API_KEY")
    llm = ChatOpenAI(
        openai_api_key=QINIU_API_KEY,
        openai_api_base=QINIU_BASE_URL,
        model=MODEL_NAME,
        temperature=0.1,
        max_tokens=200
    )
    agent = create_react_agent(model=llm, tools=tools)
    return agent

# 短期记忆
class ShortTermMemory:
    def __init__(self):
        self.ip_memory = {}

    def upgrade_action(self, ip: str, current_action: str) -> str:
        now = time.time()
        if ip not in self.ip_memory:
            return current_action
        last = self.ip_memory[ip].get("last_action")
        last_time = self.ip_memory[ip].get("last_time", 0)
        if not last or now - last_time > 60:
            return current_action
        if current_action == "log_alert_only" and last == "log_alert_only":
            return "rate_limit_ip"
        if current_action == "rate_limit_ip" and last == "rate_limit_ip":
            return "block_ip"
        return current_action

    def update(self, ip: str, action: str):
        self.ip_memory[ip] = {
            "last_action": action,
            "last_time": time.time(),
            "count": self.ip_memory.get(ip, {}).get("count", 0) + 1
        }

short_memory = ShortTermMemory()

if __name__ == "__main__":
    print("Agent Core 模块加载成功")