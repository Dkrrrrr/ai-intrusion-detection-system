from dotenv import load_dotenv
load_dotenv()

import requests
import os
import time
import subprocess
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent

QINIU_API_KEY = os.environ.get("QINIU_API_KEY", "")
QINIU_BASE_URL = os.environ.get("QINIU_BASE_URL", "https://api.qnaigc.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek/deepseek-v4-flash")


# ============================================================
# 工具定义
# ============================================================

@tool
def check_ip_reputation(ip: str) -> str:
    """查询IP地址的威胁情报，获取恶意评分和风险等级。"""
    api_key = os.getenv("ABUSEIPDB_API_KEY")

    if not api_key:
        return "威胁情报API未配置，请设置环境变量 ABUSEIPDB_API_KEY"

    url = "https://api.abuseipdb.com/api/v2/check"
    headers = {
        "Key": api_key,
        "Accept": "application/json"
    }
    params = {
        "ipAddress": ip,
        "maxAgeInDays": 30
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()

        if response.status_code == 200:
            result = data.get("data", {})
            score = result.get("abuseConfidenceScore", 0)
            country = result.get("countryCode", "未知")
            reports = result.get("totalReports", 0)

            if score > 80:
                suggestion = "高风险，建议立即封禁"
            elif score > 30:
                suggestion = "中低风险，建议限速或仅记录观察"
            else:
                suggestion = "风险较低，可仅记录"

            return f"IP {ip} 威胁评分: {score}% (共{reports}次举报), 归属地: {country}. 评估建议: {suggestion}"
        else:
            return f"情报查询失败: {data.get('errors', [{}])[0].get('detail', '未知错误')}"

    except Exception as e:
        return f"网络请求异常: {str(e)}"


@tool
def check_domain_reputation(domain: str) -> str:
    """查询域名或URL的威胁情报，获取安全评分和检测结果。"""
    api_key = os.getenv("VIRUSTOTAL_API_KEY")

    if not api_key:
        return "VirusTotal API未配置，请设置环境变量 VIRUSTOTAL_API_KEY"

    url = f"https://www.virustotal.com/api/v3/domains/{domain}"
    headers = {
        "x-apikey": api_key
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            attributes = data.get("data", {}).get("attributes", {})
            stats = attributes.get("last_analysis_stats", {})
            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            harmless = stats.get("harmless", 0)

            total_engines = malicious + suspicious + harmless + stats.get("undetected", 0)

            if malicious > 0:
                suggestion = f"高危：{malicious} 个引擎检测为恶意，建议封禁"
            elif suspicious > 0:
                suggestion = f"中危：{suspicious} 个引擎标记为可疑，建议限速观察"
            else:
                suggestion = "低危：未发现恶意检测，可正常访问"

            return f"域名 {domain} 检测结果：{malicious}/{total_engines} 个引擎报毒。{suggestion}"
        else:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "未知错误")
            return f"域名查询失败: {error_msg}"

    except Exception as e:
        return f"网络请求异常: {str(e)}"


@tool
def block_ip(ip: str) -> str:
    """封禁一个IP地址，阻止其访问系统（真实执行Windows防火墙规则）。"""
    print(f"[ACTION] 封禁 IP: {ip}")
    try:
        cmd = f'netsh advfirewall firewall add rule name="Block_{ip}" dir=in action=block remoteip={ip}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return f"已真实封禁 {ip}（Windows防火墙规则已添加）"
        else:
            return f"封禁失败: {result.stderr}"
    except Exception as e:
        return f"执行异常: {str(e)}"


@tool
def rate_limit_ip(ip: str) -> str:
    """对某个IP地址启用速率限制（当前为模拟，实际部署可对接限速策略）。"""
    print(f"[ACTION] 对 IP {ip} 启用速率限制（模拟）")
    return f"已对 {ip} 启用速率限制（模拟）"


@tool
def log_alert_only(attack_type: str, src_ip: str) -> str:
    """仅记录告警，不执行任何主动响应。"""
    print(f"[ACTION] 仅记录告警: {attack_type} from {src_ip}")
    return f"已记录 {attack_type} 攻击，源IP {src_ip}"


# 注册所有工具
tools = [check_ip_reputation, check_domain_reputation, block_ip, rate_limit_ip, log_alert_only]


# ============================================================
# RAG 向量数据库（延迟初始化，支持 --reload 模式）
# ============================================================

_rag_initialized = False
embedding_model = None
client = None
collection_name = "incident_memory"


def init_rag():
    """延迟初始化 RAG 组件，只在第一次调用时执行"""
    global _rag_initialized, embedding_model, client

    if _rag_initialized:
        return

    print("[RAG] 正在初始化...")

    # 1. 延迟导入（避免在模块加载时阻塞）
    from sentence_transformers import SentenceTransformer
    from pymilvus import MilvusClient, DataType

    # 2. 加载嵌入模型
    print("[RAG] 正在加载嵌入模型 all-MiniLM-L6-v2 ...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("[RAG] 嵌入模型加载成功")

    # 3. 连接 Milvus
    client = MilvusClient(uri="./milvus_data.db")
    print("[RAG] Milvus 连接成功")

    # 4. 检查并重建 collection
    if client.has_collection(collection_name):
        client.drop_collection(collection_name)
        print(f"[RAG] 已删除旧的 collection: {collection_name}")

    # 5. 创建 Schema
    schema = client.create_schema(auto_id=True, enable_dynamic_field=True)
    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=384)
    schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=2000)
    schema.add_field(field_name="attack_type", datatype=DataType.VARCHAR, max_length=100)
    schema.add_field(field_name="action", datatype=DataType.VARCHAR, max_length=50)

    # 6. 创建 Collection
    client.create_collection(
        collection_name=collection_name,
        schema=schema
    )

    # 7. 创建索引
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="HNSW",
        metric_type="COSINE",
        params={"M": 16, "efConstruction": 200}
    )
    client.create_index(
        collection_name=collection_name,
        index_params=index_params
    )

    print("[RAG] HNSW 索引创建成功")
    print(f"[RAG] Collection 已就绪，当前存储 {client.get_collection_stats(collection_name).get('row_count', 0)} 条记录")

    _rag_initialized = True


def add_incident_to_milvus(attack_type: str, action: str, result: str) -> bool:
    """将新的处置记录存入 Milvus 向量数据库"""
    init_rag()
    try:
        doc_text = f"攻击类型: {attack_type}, 处置动作: {action}, 结果摘要: {result[:150]}"
        embedding = embedding_model.encode(doc_text).tolist()

        client.insert(
            collection_name=collection_name,
            data=[{
                "vector": embedding,
                "text": doc_text[:1900],
                "attack_type": attack_type,
                "action": action
            }]
        )
        print(f"[RAG] 已存入记录: {attack_type} -> {action}")
        return True
    except Exception as e:
        print(f"[RAG] 存入失败: {e}")
        return False


def retrieve_similar_incidents_milvus(query: str, k: int = 2) -> list:
    """根据查询文本检索最相似的历史处置案例"""
    init_rag()
    try:
        stats = client.get_collection_stats(collection_name)
        if stats.get("row_count", 0) == 0:
            return []

        query_embedding = embedding_model.encode(query).tolist()

        results = client.search(
            collection_name=collection_name,
            data=[query_embedding],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"ef": 64}},
            limit=k,
            output_fields=["text", "attack_type", "action"]
        )

        similar_cases = []
        for hit in results[0]:
            similar_cases.append({
                "text": hit.get("entity", {}).get("text", ""),
                "attack_type": hit.get("entity", {}).get("attack_type", ""),
                "action": hit.get("entity", {}).get("action", ""),
                "distance": hit.get("distance", 0)
            })

        print(f"[RAG] 检索到 {len(similar_cases)} 条相似案例")
        return similar_cases

    except Exception as e:
        print(f"[RAG] 检索失败: {e}")
        return []


def format_rag_context(cases: list) -> str:
    """将检索到的案例格式化为系统提示词中的上下文"""
    if not cases:
        return "【历史相似案例参考】\n无相似历史案例。"

    lines = ["【历史相似案例参考】"]
    for i, case in enumerate(cases, 1):
        confidence = "高" if case["distance"] > 0.85 else "中" if case["distance"] > 0.65 else "低"
        lines.append(f"案例{i}（相似度{confidence}）:")
        lines.append(f"  - 攻击类型: {case['attack_type']}")
        lines.append(f"  - 历史处置: {case['action']}")
        lines.append(f"  - 详情: {case['text'][:80]}...")

    return "\n".join(lines)


def get_rag_stats() -> dict:
    """获取 RAG 知识库的统计信息"""
    init_rag()
    stats = client.get_collection_stats(collection_name)
    return {
        "total_records": stats.get("row_count", 0),
        "collection_name": collection_name,
        "is_initialized": _rag_initialized
    }


# ============================================================
# 长期记忆（文本存储，用于关键词匹配兜底）
# ============================================================

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


# ============================================================
# Agent 创建函数
# ============================================================

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


# ============================================================
# 短期记忆（60秒窗口升级策略）
# ============================================================

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