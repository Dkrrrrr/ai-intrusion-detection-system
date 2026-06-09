// frontend/src/App.jsx
import React, { useState, useEffect } from 'react';
import { predict, agentDecide, agentExplain, getStats } from './api';
import './index.css';  // 沿用默认的简单样式

function App() {
  // 各个模块的状态
  const [predFeatures, setPredFeatures] = useState('');
  const [predResult, setPredResult] = useState(null);
  const [decisionAttack, setDecisionAttack] = useState('');
  const [decisionIp, setDecisionIp] = useState('');
  const [decisionRisk, setDecisionRisk] = useState('高');
  const [decisionResult, setDecisionResult] = useState(null);
  const [explainAttack, setExplainAttack] = useState('');
  const [explainFeatures, setExplainFeatures] = useState('');
  const [explainResult, setExplainResult] = useState('');
  const [stats, setStats] = useState({ total_predictions: 0, total_attacks_detected: 0, recent_decisions: [] });
  const [loading, setLoading] = useState(false);

  // 获取统计信息
  const loadStats = async () => {
    try {
      const data = await getStats();
      setStats(data);
    } catch (err) {
      console.error('获取统计失败', err);
    }
  };
  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 5000); // 每5秒刷新一次统计
    return () => clearInterval(interval);
  }, []);

  // 模型预测
  const handlePredict = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      // 将用户输入的逗号分隔字符串转为浮点数数组
      const featuresArray = predFeatures.split(',').map(Number);
      if (featuresArray.some(isNaN)) throw new Error('请输入有效的数字，用逗号分隔');
      const result = await predict(featuresArray);
      setPredResult(result);
    } catch (err) {
      alert('预测失败：' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Agent 决策
  const handleDecide = async (e) => {
    e.preventDefault();
    if (!decisionAttack || !decisionIp) return alert('请填写攻击类型和源IP');
    setLoading(true);
    try {
      const result = await agentDecide(decisionAttack, decisionIp, decisionRisk);
      setDecisionResult(result);
    } catch (err) {
      alert('决策失败：' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // AI 解释
  const handleExplain = async (e) => {
    e.preventDefault();
    if (!explainAttack) return alert('请填写攻击类型');
    let featuresObj = {};
    if (explainFeatures.trim()) {
      try {
        // 用户输入 JSON 格式，例如 {"bytes_sent": 1500, "packets": 10}
        featuresObj = JSON.parse(explainFeatures);
      } catch (err) {
        alert('特征格式错误，请输入合法的 JSON 对象');
        return;
      }
    }
    setLoading(true);
    try {
      const result = await agentExplain(explainAttack, featuresObj);
      setExplainResult(result.explanation);
    } catch (err) {
      alert('解释失败：' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <h1>🛡️ 智能入侵检测系统 (IDS) 控制台</h1>
      <div className="grid">
        {/* 模块1: 模型预测 */}
        <div className="card">
          <h2>🔮 模型预测</h2>
          <form onSubmit={handlePredict}>
            <label>特征向量（逗号分隔，顺序与训练时一致）</label>
            <textarea
              rows="3"
              value={predFeatures}
              onChange={(e) => setPredFeatures(e.target.value)}
              placeholder="例如: 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0"
            />
            <button type="submit" disabled={loading}>预测</button>
          </form>
          {predResult && (
            <div className="result">
              <p><strong>预测结果：</strong> {predResult.prediction}</p>
              <p><strong>概率：</strong> 正常 {predResult.probability?.normal?.toFixed(4)}，攻击 {predResult.probability?.attack?.toFixed(4)}</p>
            </div>
          )}
        </div>

        {/* 模块2: Agent 决策 */}
        <div className="card">
          <h2>🤖 Agent 决策 (响应动作)</h2>
          <form onSubmit={handleDecide}>
            <label>攻击类型</label>
            <input value={decisionAttack} onChange={(e) => setDecisionAttack(e.target.value)} placeholder="例如: dos, probe, r2l, u2r" />
            <label>源 IP</label>
            <input value={decisionIp} onChange={(e) => setDecisionIp(e.target.value)} placeholder="例如: 192.168.1.100" />
            <label>风险等级</label>
            <select value={decisionRisk} onChange={(e) => setDecisionRisk(e.target.value)}>
              <option value="高">高</option>
              <option value="中">中</option>
              <option value="低">低</option>
            </select>
            <button type="submit" disabled={loading}>决策</button>
          </form>
          {decisionResult && (
            <div className="result">
              <p><strong>最终动作：</strong> {decisionResult.action}</p>
              <details>
                <summary>Agent 完整响应</summary>
                <pre>{decisionResult.full_response}</pre>
              </details>
            </div>
          )}
        </div>

        {/* 模块3: AI 解释 */}
        <div className="card">
          <h2>🧠 AI 攻击解释</h2>
          <form onSubmit={handleExplain}>
            <label>攻击类型</label>
            <input value={explainAttack} onChange={(e) => setExplainAttack(e.target.value)} placeholder="例如: dos" />
            <label>特征 (JSON 对象，可选)</label>
            <textarea rows="2" value={explainFeatures} onChange={(e) => setExplainFeatures(e.target.value)} placeholder='{"bytes_sent":1500, "packets":10}' />
            <button type="submit" disabled={loading}>生成解释</button>
          </form>
          {explainResult && (
            <div className="result">
              <p><strong>AI 解释：</strong> {explainResult}</p>
            </div>
          )}
        </div>

        {/* 模块4: 统计信息 */}
        <div className="card">
          <h2>📊 系统统计</h2>
          <p>总预测次数：{stats.total_predictions}</p>
          <p>检测到的攻击总数：{stats.total_attacks_detected}</p>
          <h4>最近 5 条决策记录</h4>
          <ul className="decision-list">
            {stats.recent_decisions.slice(0,5).map((dec, idx) => (
              <li key={idx}>
                {dec.attack} | {dec.ip} → {dec.action} (风险:{dec.risk})
              </li>
            ))}
          </ul>
          <button onClick={loadStats} style={{marginTop:'10px'}}>刷新统计</button>
        </div>
      </div>
      {loading && <div className="loading-overlay">处理中...</div>}
    </div>
  );
}

export default App;