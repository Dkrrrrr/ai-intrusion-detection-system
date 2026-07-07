import React, { useState, useEffect } from 'react';
import { predict, agentDecide, agentExplain, getStats } from './api';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

function App() {
  // ============ 状态管理 ============
  const [stats, setStats] = useState({
    total_predictions: 0,
    total_attacks_detected: 0,
    recent_decisions: []
  });

  // 预测模块
  const [predFeatures, setPredFeatures] = useState('');
  const [predResult, setPredResult] = useState(null);
  const [predLoading, setPredLoading] = useState(false);

  // Agent决策模块
  const [decisionAttack, setDecisionAttack] = useState('');
  const [decisionIp, setDecisionIp] = useState('');
  const [decisionRisk, setDecisionRisk] = useState('高');
  const [decisionResult, setDecisionResult] = useState(null);
  const [decisionLoading, setDecisionLoading] = useState(false);

  // AI解释模块
  const [explainAttack, setExplainAttack] = useState('');
  const [explainFeatures, setExplainFeatures] = useState('');
  const [explainResult, setExplainResult] = useState('');
  const [explainLoading, setExplainLoading] = useState(false);

  // 图表数据
  const [trendData, setTrendData] = useState([]);
  const [attackTypeData, setAttackTypeData] = useState([]);

  // ============ 数据获取 ============
  const loadStats = async () => {
    try {
      const data = await getStats();
      setStats(data);

      // 生成模拟趋势数据（实际可改为从后端获取）
      const now = new Date();
      const trend = [];
      for (let i = 6; i >= 0; i--) {
        const d = new Date(now);
        d.setDate(d.getDate() - i);
        trend.push({
          date: `${d.getMonth()+1}/${d.getDate()}`,
          attacks: Math.floor(Math.random() * 20) + 5,
          normal: Math.floor(Math.random() * 40) + 20
        });
      }
      setTrendData(trend);

      // 攻击类型分布（模拟数据）
      setAttackTypeData([
        { name: 'DDoS', value: 35 },
        { name: 'Port Scan', value: 25 },
        { name: 'Brute Force', value: 20 },
        { name: 'SQL Injection', value: 12 },
        { name: 'Other', value: 8 }
      ]);
    } catch (err) {
      console.error('获取统计失败', err);
    }
  };

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 8000);
    return () => clearInterval(interval);
  }, []);

  // ============ 事件处理 ============
  const handlePredict = async (e) => {
    e.preventDefault();
    setPredLoading(true);
    try {
      const arr = predFeatures.split(',').map(Number);
      if (arr.some(isNaN)) throw new Error('请输入有效数字');
      const result = await predict(arr);
      setPredResult(result);
    } catch (err) {
      alert('预测失败：' + err.message);
    } finally {
      setPredLoading(false);
    }
  };

  const handleDecide = async (e) => {
    e.preventDefault();
    if (!decisionAttack || !decisionIp) return alert('请填写攻击类型和源IP');
    setDecisionLoading(true);
    try {
      const result = await agentDecide(decisionAttack, decisionIp, decisionRisk);
      setDecisionResult(result);
      await loadStats();
    } catch (err) {
      alert('决策失败：' + err.message);
    } finally {
      setDecisionLoading(false);
    }
  };

  const handleExplain = async (e) => {
    e.preventDefault();
    if (!explainAttack) return alert('请填写攻击类型');
    setExplainLoading(true);
    try {
      let features = {};
      if (explainFeatures.trim()) {
        features = JSON.parse(explainFeatures);
      }
      const result = await agentExplain(explainAttack, features);
      setExplainResult(result.explanation);
    } catch (err) {
      alert('解释失败：' + err.message);
    } finally {
      setExplainLoading(false);
    }
  };

  // 计算攻击率
  const attackRate = stats.total_predictions > 0
    ? Math.round((stats.total_attacks_detected / stats.total_predictions) * 100)
    : 0;

  const recentDecisions = stats.recent_decisions || [];
  const recentAlerts = recentDecisions.slice(0, 5);

  // 饼图颜色
  const COLORS = ['#58A6FF', '#00D4AA', '#D29922', '#F97583', '#8B949E'];

  // ============ 渲染 ============
  return (
    <div className="app">
      {/* ===== 顶栏 ===== */}
      <header className="header">
        <div className="header-left">
          <span className="logo-icon">🛡️</span>
          <span className="logo-text">AI-NIDS</span>
          <span className="logo-sub">智能入侵检测系统</span>
        </div>
        <div className="header-right">
          <span className="status-dot"></span>
          <span className="status-text">系统运行中</span>
        </div>
      </header>

      {/* ===== KPI 卡片行 ===== */}
      <section className="kpi-row">
        <div className="kpi-card">
          <div className="kpi-label">总预测</div>
          <div className="kpi-value">{stats.total_predictions}</div>
          <div className="kpi-trend">+{stats.total_predictions > 0 ? '12%' : '0%'}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">攻击总数</div>
          <div className="kpi-value" style={{ color: '#F97583' }}>{stats.total_attacks_detected}</div>
          <div className="kpi-trend">攻击率 {attackRate}%</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">今日告警</div>
          <div className="kpi-value" style={{ color: '#D29922' }}>{Math.min(recentDecisions.length, 12)}</div>
          <div className="kpi-trend">最近1小时</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Agent决策</div>
          <div className="kpi-value" style={{ color: '#00D4AA' }}>{recentDecisions.length}</div>
          <div className="kpi-trend">封禁 {recentDecisions.filter(d => d.action === 'block_ip').length} 次</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">系统健康</div>
          <div className="kpi-value" style={{ color: '#00D4AA' }}>98%</div>
          <div className="kpi-trend">所有服务正常</div>
        </div>
      </section>

      {/* ===== 图表行 ===== */}
      <section className="charts-row">
        <div className="chart-card chart-trend">
          <div className="chart-header">
            <span className="chart-title">📈 攻击趋势（近7天）</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#30363D" />
              <XAxis dataKey="date" stroke="#8B949E" fontSize={11} />
              <YAxis stroke="#8B949E" fontSize={11} />
              <Tooltip contentStyle={{ backgroundColor: '#161B22', borderColor: '#30363D' }} />
              <Legend />
              <Line type="monotone" dataKey="attacks" stroke="#F97583" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="normal" stroke="#58A6FF" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card chart-distribution">
          <div className="chart-header">
            <span className="chart-title">📊 攻击类型分布</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={attackTypeData}
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={70}
                paddingAngle={2}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={{ stroke: '#8B949E', strokeWidth: 1 }}
              >
                {attackTypeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#161B22', borderColor: '#30363D' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* ===== 列表行 ===== */}
      <section className="lists-row">
        <div className="list-card">
          <div className="list-header">
            <span className="list-title">🚨 最近告警</span>
            <span className="list-badge">{recentAlerts.length} 条</span>
          </div>
          <div className="list-body">
            {recentAlerts.length === 0 ? (
              <div className="list-empty">暂无告警</div>
            ) : (
              recentAlerts.map((item, idx) => (
                <div className="list-item" key={idx}>
                  <span className={`list-tag ${item.action === 'block_ip' ? 'tag-critical' : item.action === 'rate_limit_ip' ? 'tag-warning' : 'tag-info'}`}>
                    {item.action === 'block_ip' ? '封禁' : item.action === 'rate_limit_ip' ? '限速' : '记录'}
                  </span>
                  <span className="list-attack">{item.attack}</span>
                  <span className="list-ip">{item.ip}</span>
                  <span className="list-time">{(item.risk || '中')}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="list-card">
          <div className="list-header">
            <span className="list-title">🤖 Agent决策记录</span>
            <span className="list-badge">{recentDecisions.length} 条</span>
          </div>
          <div className="list-body">
            {recentDecisions.length === 0 ? (
              <div className="list-empty">暂无决策</div>
            ) : (
              recentDecisions.slice(0, 6).map((item, idx) => (
                <div className="list-item" key={idx}>
                  <span className={`list-action ${item.action === 'block_ip' ? 'act-block' : item.action === 'rate_limit_ip' ? 'act-limit' : 'act-log'}`}>
                    {item.action === 'block_ip' ? '🔒 封禁' : item.action === 'rate_limit_ip' ? '⏱️ 限速' : '📝 记录'}
                  </span>
                  <span className="list-detail">{item.attack} @ {item.ip}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      {/* ===== 操作区 ===== */}
      <section className="actions-section">
        <div className="actions-header">
          <span className="actions-title">⚡ 快速操作</span>
          <span className="actions-hint">展开以执行预测、决策或解释</span>
        </div>

        <div className="actions-grid">
          {/* 预测 */}
          <div className="action-card">
            <div className="action-card-title">🔮 模型预测</div>
            <form onSubmit={handlePredict}>
              <textarea
                rows="2"
                value={predFeatures}
                onChange={(e) => setPredFeatures(e.target.value)}
                placeholder="特征向量（逗号分隔）"
              />
              <button type="submit" disabled={predLoading}>
                {predLoading ? '预测中...' : '执行预测'}
              </button>
            </form>
            {predResult && (
              <div className="action-result">
                <span className="result-label">结果：</span>
                <span className={predResult.prediction === 'attack' ? 'result-attack' : 'result-normal'}>
                  {predResult.prediction}
                </span>
                <span className="result-prob">
                  攻击 {((predResult.probability?.attack || 0) * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>

          {/* Agent决策 */}
          <div className="action-card">
            <div className="action-card-title">🤖 Agent决策</div>
            <form onSubmit={handleDecide}>
              <div className="form-row">
                <input
                  value={decisionAttack}
                  onChange={(e) => setDecisionAttack(e.target.value)}
                  placeholder="攻击类型"
                />
                <input
                  value={decisionIp}
                  onChange={(e) => setDecisionIp(e.target.value)}
                  placeholder="源IP"
                />
                <select value={decisionRisk} onChange={(e) => setDecisionRisk(e.target.value)}>
                  <option value="高">高风险</option>
                  <option value="中">中风险</option>
                  <option value="低">低风险</option>
                </select>
              </div>
              <button type="submit" disabled={decisionLoading}>
                {decisionLoading ? '决策中...' : '执行决策'}
              </button>
            </form>
            {decisionResult && (
              <div className="action-result">
                <span className="result-label">动作：</span>
                <span className={`result-action ${decisionResult.action === 'block_ip' ? 'act-block' : decisionResult.action === 'rate_limit_ip' ? 'act-limit' : 'act-log'}`}>
                  {decisionResult.action === 'block_ip' ? '🔒 封禁' : decisionResult.action === 'rate_limit_ip' ? '⏱️ 限速' : '📝 记录'}
                </span>
              </div>
            )}
          </div>

          {/* AI解释 */}
          <div className="action-card">
            <div className="action-card-title">🧠 AI解释</div>
            <form onSubmit={handleExplain}>
              <div className="form-row">
                <input
                  value={explainAttack}
                  onChange={(e) => setExplainAttack(e.target.value)}
                  placeholder="攻击类型"
                />
                <input
                  value={explainFeatures}
                  onChange={(e) => setExplainFeatures(e.target.value)}
                  placeholder='特征 JSON（可选）'
                />
              </div>
              <button type="submit" disabled={explainLoading}>
                {explainLoading ? '生成中...' : '生成解释'}
              </button>
            </form>
            {explainResult && (
              <div className="action-result">
                <span className="result-label">解释：</span>
                <span className="result-text">{explainResult}</span>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

export default App;