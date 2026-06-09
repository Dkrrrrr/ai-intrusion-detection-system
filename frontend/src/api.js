// frontend/src/api.js
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

// 预测
export async function predict(features) {
  const response = await axios.post(`${API_BASE}/predict`, { features });
  return response.data;
}

// Agent 决策
export async function agentDecide(attackType, srcIp, riskLevel = '高') {
  const response = await axios.post(`${API_BASE}/agent/decide`, {
    attack_type: attackType,
    src_ip: srcIp,
    risk_level: riskLevel,
  });
  return response.data;
}

// AI 解释
export async function agentExplain(attackType, features) {
  const response = await axios.post(`${API_BASE}/agent/explain`, {
    attack_type: attackType,
    features: features,
  });
  return response.data;
}

// 统计信息
export async function getStats() {
  const response = await axios.get(`${API_BASE}/stats`);
  return response.data;
}