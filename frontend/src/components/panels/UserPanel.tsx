import { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useAuth } from '../../contexts/AuthContext';
import { useTrade } from '../../contexts/TradeContext';
import { logger } from '../../utils/logger';
import { useJojoModal } from '../JojoModal';
import { useJojoCapitalModal } from '../JojoCapitalModal';

interface CapitalHistory {
  date: string;
  capital: number;  // 总资产
  available_funds?: number;  // 可用资金
  position_value?: number;  // 持仓市值
}

interface CapitalInfo {
  capital: number;  // 总资产（兼容）
  total_assets: number;  // 总资产
  available_funds: number;  // 可用资金
  position_value: number;  // 持仓市值
}

interface UserPanelProps {
  compact?: boolean;
  showChart?: boolean;
}

export default function UserPanel({ compact = false, showChart = false }: UserPanelProps) {
  const { user } = useAuth();
  const { confirm, Modal } = useJojoModal();
  const { openModal: openCapitalModal, Modal: CapitalModal } = useJojoCapitalModal();
  const [capitalInfo, setCapitalInfo] = useState<CapitalInfo>({
    capital: 0,
    total_assets: 0,
    available_funds: 0,
    position_value: 0
  });
  const [history, setHistory] = useState<CapitalHistory[]>([]);
  const [chartMode, setChartMode] = useState<'single' | 'compare'>('single');
  const [period, setPeriod] = useState<'1m' | '3m' | '6m' | '1y' | 'all'>('all');
  const [compareData, setCompareData] = useState<any[]>([]);
  const [compareStrategies, setCompareStrategies] = useState<Array<{ id: number; name: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [emailAlertsEnabled, setEmailAlertsEnabled] = useState<boolean>(false);
  const { _userPanelRefreshKey, refreshUserPanel, refreshAnalysis, effectiveStrategyId, strategies } = useTrade();

  useEffect(() => {
    if (showChart && chartMode === 'compare') {
      fetchCompareCapitalData();
    } else {
      fetchCapitalData(getStartDate(period));
    }
    fetchUserProfile();
  }, [_userPanelRefreshKey, chartMode, period, effectiveStrategyId, showChart]); // 当refresh key变化时刷新

  const fetchUserProfile = async () => {
    try {
      const response = await axios.get('/api/user/profile');
      setEmailAlertsEnabled(response.data.email_alerts_enabled || false);
    } catch (error) {
      logger.error('❌ [UserPanel] 获取用户设置失败', error);
    }
  };

  const getStartDate = (p: '1m' | '3m' | '6m' | '1y' | 'all') => {
    if (p === 'all') return undefined;
    const d = new Date();
    if (p === '1y') d.setFullYear(d.getFullYear() - 1);
    if (p === '6m') d.setMonth(d.getMonth() - 6);
    if (p === '3m') d.setMonth(d.getMonth() - 3);
    if (p === '1m') d.setMonth(d.getMonth() - 1);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  };

  const fetchCapitalData = async (startDate?: string) => {
    try {
      logger.info('💰 [UserPanel] 获取资金数据...');
      if (effectiveStrategyId == null) {
        setCapitalInfo({
          capital: 0,
          total_assets: 0,
          available_funds: 0,
          position_value: 0,
        });
        setHistory([]);
        return;
      }
      const params: any = {};
      if (effectiveStrategyId != null) params.strategy_id = effectiveStrategyId;
      if (startDate) params.start_date = startDate;
      const [capitalRes, historyRes] = await Promise.all([
        axios.get('/api/user/capital', { params }),
        axios.get('/api/user/capital-history', { params })
      ]);
      logger.info('✅ [UserPanel] 资金数据获取成功', {
        total_assets: capitalRes.data.total_assets,
        available_funds: capitalRes.data.available_funds,
        position_value: capitalRes.data.position_value,
        historyCount: historyRes.data.length
      });
      setCapitalInfo({
        capital: capitalRes.data.capital,
        total_assets: capitalRes.data.total_assets || capitalRes.data.capital,
        available_funds: capitalRes.data.available_funds || capitalRes.data.capital,
        position_value: capitalRes.data.position_value || 0
      });
      setHistory(historyRes.data);
    } catch (error: any) {
      logger.error('❌ [UserPanel] 获取资金数据失败', error.response?.data || error.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchCompareCapitalData = async () => {
    try {
      const startDate = getStartDate(period);
      const params: any = { market: 'stock' };
      if (startDate) params.start_date = startDate;
      const res = await axios.get('/api/user/strategies/capital-histories', { params });
      const seriesById = (res.data?.series_by_strategy_id ?? {}) as Record<string, Array<{ date: string; capital: number }>>;
      const strat = (res.data?.strategies ?? []) as Array<{ id: number; name: string }>;
      setCompareStrategies(strat.map((s) => ({ id: s.id, name: s.name })));

      const rowsByDate = new Map<string, any>();
      for (const s of strat) {
        const series = seriesById[String(s.id)] ?? [];
        for (const p of series) {
          const row = rowsByDate.get(p.date) ?? { date: p.date };
          row[`s_${s.id}`] = p.capital;
          rowsByDate.set(p.date, row);
        }
      }
      const rows = Array.from(rowsByDate.values()).sort((a, b) => String(a.date).localeCompare(String(b.date)));
      setCompareData(rows);
    } catch (error: any) {
      logger.error('❌ [UserPanel] 获取策略对比资金曲线失败', error.response?.data || error.message);
      setCompareData([]);
      setCompareStrategies([]);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleEmailAlerts = async () => {
    try {
      const newValue = !emailAlertsEnabled;
      await axios.post(`/api/user/email-alerts?enabled=${newValue}`);
      setEmailAlertsEnabled(newValue);
      logger.info(`✅ [UserPanel] 邮箱提醒已${newValue ? '开启' : '关闭'}`);
      
      if (newValue) {
        alert('✅ 邮箱提醒已开启！\n\n当价格触及止损/止盈时，您将收到邮件通知。\n\n⚠️ 注意：需要后端配置SMTP服务才能发送邮件。');
      }
    } catch (error) {
      logger.error('❌ [UserPanel] 更新邮箱提醒设置失败', error);
      alert('更新失败，请稍后重试');
    }
  };
  
  const handleTestEmail = async () => {
    try {
      logger.info('📧 [UserPanel] 发送测试邮件...');
      await axios.post('/api/user/test-email');
      alert('✅ 测试邮件已发送！\n\n请检查您的邮箱（包括垃圾邮件文件夹）。\n\n如果没有收到，请检查后端.env文件中的SMTP配置。');
    } catch (error: any) {
      logger.error('❌ [UserPanel] 测试邮件发送失败', error);
      const errorMsg = error.response?.data?.detail || '发送失败';
      alert(`❌ 测试邮件发送失败\n\n错误信息：${errorMsg}\n\n请检查后端.env文件中的SMTP配置。`);
    }
  };

  const handleUpdateCapital = async () => {
    logger.info('🖱️ [UserPanel] 点击更新资金按钮');
    try {
      if (effectiveStrategyId == null) {
        await confirm('⚠️ 需要策略', '请先创建并选择策略后再设置资金锚点');
        return;
      }
      const result = await openCapitalModal();
      
      if (!result) {
        logger.info('⚠️ [UserPanel] 用户取消');
        return;
      }
      
      const { capital: capitalStr, date: dateStr } = result;
      logger.info(`📝 [UserPanel] 用户输入 - 资金: ${capitalStr}, 日期: ${dateStr}`);
      
      if (!capitalStr || isNaN(parseFloat(capitalStr))) {
        await confirm('❌ 输入无效', '请输入有效的资金金额');
        return;
      }
      
      const newCapital = parseFloat(capitalStr);
      let updateDate: string | null = null;
      
      if (dateStr && dateStr.trim() !== '') {
        // 简单的日期格式验证
        if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr.trim())) {
          await confirm('❌ 格式错误', '日期格式不正确，请使用 YYYY-MM-DD 格式');
          return;
        }
        updateDate = dateStr.trim();
      }
      
      logger.info(`💰 [UserPanel] 设置初始资金: ${newCapital} (日期: ${updateDate || '今天'})`);
      const requestBody: { capital: number; date?: string } = { 
        capital: newCapital
      };
      // 只有当用户提供了日期时才添加到请求体中
      if (updateDate) {
        requestBody.date = updateDate;
      }
      
      const params = effectiveStrategyId != null ? { strategy_id: effectiveStrategyId } : undefined;
      const response = await axios.post('/api/user/capital', requestBody, { params });
      logger.info('✅ [UserPanel] 初始资金设置成功', response.data);
      
      // 触发所有相关面板的刷新
      refreshUserPanel(); // 刷新用户面板（资金曲线）
      refreshAnalysis(); // 刷新AI分析（资金曲线变化会影响分析）
      
      // 等待一小段时间确保后端已完成资金曲线重新计算
      setTimeout(() => {
        if (showChart && chartMode === 'compare') {
          fetchCompareCapitalData();
        } else {
          fetchCapitalData(getStartDate(period));
        }
      }, 500);
    } catch (error: any) {
      logger.error('❌ [UserPanel] 资金设置失败', error);
      await confirm('❌ 设置失败', error.response?.data?.detail || error.message || '设置失败');
    }
  };

  if (loading) {
    return (
      <>
        <div className="jojo-card p-6 text-center">
          <div className="text-jojo-gold animate-jojo-pulse">加载中...</div>
        </div>
        <Modal />
        <CapitalModal />
      </>
    );
  }

  // 紧凑模式：只显示账户信息
  if (compact) {
    return (
      <>
      <div className="jojo-card p-3 h-full flex flex-col">
        <h2 className="jojo-title text-lg mb-2">账户</h2>
        <div className="space-y-2">
          <div>
            <p className="text-gray-300 text-xs mb-1">总资产</p>
            <p className="text-2xl font-bold text-jojo-gold">
              ¥{capitalInfo.total_assets.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-jojo-gold/30">
            <div>
              <p className="text-gray-400 text-xs mb-0.5">可用资金</p>
              <p className="text-green-400 font-semibold text-sm">
                ¥{capitalInfo.available_funds.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
              </p>
            </div>
            <div>
              <p className="text-gray-400 text-xs mb-0.5">持仓市值</p>
              <p className="text-blue-400 font-semibold text-sm">
                ¥{capitalInfo.position_value.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
              </p>
            </div>
          </div>
          <div className="pt-2 border-t border-jojo-gold/30">
            <p className="text-gray-300 text-xs mb-0.5">用户名</p>
            <p className="text-jojo-gold font-semibold text-sm">{user?.username}</p>
            <p className="text-gray-300 text-xs mb-0.5 mt-1">邮箱</p>
            <p className="text-gray-300 text-xs">{user?.email}</p>
          </div>
          <button
            onClick={handleUpdateCapital}
            className="jojo-button w-full text-xs py-1"
          >
            更新资金
          </button>
        </div>
      </div>
      <Modal />
      <CapitalModal />
      </>
    );
  }

  // 图表模式：显示资金曲线
  if (showChart) {
    return (
      <>
      <div className="jojo-card p-3 h-full flex flex-col">
        <div className="flex items-center justify-between mb-2">
          <h2 className="jojo-title text-lg">资金成长曲线</h2>
          <div className="flex items-center gap-2">
            <select
              value={chartMode}
              onChange={(e) => {
                const next = e.target.value === 'compare' ? 'compare' : 'single';
                setLoading(true);
                setChartMode(next);
                if (next === 'compare' && strategies.length < 2) {
                  setChartMode('single');
                }
              }}
              className="jojo-input text-xs py-1"
              disabled={strategies.length < 2}
            >
              <option value="single">当前策略</option>
              <option value="compare">全部策略对比</option>
            </select>
            <select value={period} onChange={(e) => setPeriod(e.target.value as any)} className="jojo-input text-xs py-1">
              <option value="1m">近1月</option>
              <option value="3m">近3月</option>
              <option value="6m">近6月</option>
              <option value="1y">近1年</option>
              <option value="all">全部</option>
            </select>
          </div>
        </div>
        <div className="flex-1 min-h-[160px]">
          {chartMode === 'compare' ? (
            compareData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={compareData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#FFD700" opacity={0.3} />
                  <XAxis dataKey="date" stroke="#FFD700" style={{ fill: '#FFD700' }} />
                  <YAxis stroke="#FFD700" style={{ fill: '#FFD700' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1a1a2e',
                      border: '2px solid #FFD700',
                      borderRadius: '8px',
                      color: '#FFD700'
                    }}
                  />
                  <Legend wrapperStyle={{ color: '#FFD700' }} />
                  {compareStrategies.map((s, idx) => (
                    <Line
                      key={s.id}
                      type="monotone"
                      dataKey={`s_${s.id}`}
                      stroke={idx % 2 === 0 ? '#FFD700' : '#10B981'}
                      strokeWidth={2}
                      dot={false}
                      name={s.name}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                <p>暂无资金历史数据</p>
              </div>
            )
          ) : history.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke="#FFD700" opacity={0.3} />
                <XAxis 
                  dataKey="date" 
                  stroke="#FFD700"
                  style={{ fill: '#FFD700' }}
                />
                <YAxis 
                  stroke="#FFD700"
                  style={{ fill: '#FFD700' }}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1a1a2e', 
                    border: '2px solid #FFD700',
                    borderRadius: '8px',
                    color: '#FFD700'
                  }}
                />
                <Legend 
                  wrapperStyle={{ color: '#FFD700' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="capital" 
                  stroke="#FFD700" 
                  strokeWidth={3}
                  dot={{ fill: '#FFD700', r: 4 }}
                  activeDot={{ r: 6 }}
                  name="资金"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              <p>暂无资金历史数据</p>
            </div>
          )}
        </div>
      </div>
      <Modal />
      <CapitalModal />
      </>
    );
  }

  // 完整模式：显示所有信息
  return (
    <>
    <div className="space-y-6">
      <div className="jojo-card p-6">
        <h2 className="jojo-title text-2xl mb-4">用户信息</h2>
        <div className="space-y-3">
          <p><span className="font-medium text-jojo-gold">用户名:</span> <span className="text-white">{user?.username}</span></p>
          <p><span className="font-medium text-jojo-gold">邮箱:</span> <span className="text-white">{user?.email}</span></p>
          
          {/* 邮箱提醒开关 - 更明显的按钮 */}
          <div className="pt-3 border-t border-jojo-gold/30">
            <div className="mb-3">
              <p className="font-medium text-jojo-gold mb-1">📧 邮箱闹铃提醒</p>
              <p className="text-xs text-gray-400 mb-3">价格触及止损/止盈时发送邮件通知</p>
              
              {/* 大按钮开关 */}
              <button
                onClick={handleToggleEmailAlerts}
                className={`w-full py-3 px-4 rounded-lg font-semibold text-sm transition-all border-2 ${
                  emailAlertsEnabled 
                    ? 'bg-green-600 hover:bg-green-500 text-white border-green-400 shadow-lg shadow-green-500/50' 
                    : 'bg-gray-700 hover:bg-gray-600 text-gray-300 border-gray-600'
                }`}
              >
                <div className="flex items-center justify-center space-x-2">
                  <span className="text-xl">{emailAlertsEnabled ? '✓' : '○'}</span>
                  <span>{emailAlertsEnabled ? '邮件提醒已开启' : '点击开启邮件提醒'}</span>
                </div>
              </button>
            </div>
            
            {emailAlertsEnabled && (
              <div className="space-y-2">
                <div className="flex items-center space-x-2 text-xs text-green-400 bg-green-500/10 px-3 py-2 rounded">
                  <span>✓</span>
                  <span>邮件通知已启用，价格提醒将发送到: {user?.email}</span>
                </div>
                <button
                  onClick={handleTestEmail}
                  className="w-full px-4 py-2 bg-jojo-purple/50 hover:bg-jojo-purple border-2 border-jojo-gold/50 hover:border-jojo-gold rounded-lg text-jojo-gold font-semibold text-sm transition-all shadow-lg"
                >
                  📧 发送测试邮件
                </button>
              </div>
            )}
            {!emailAlertsEnabled && (
              <div className="mt-2 text-xs text-gray-500 bg-gray-800/50 px-3 py-2 rounded border border-gray-700">
                <p className="mb-1">⚠️ 邮件提醒未开启</p>
                <p className="text-gray-600">需要后端配置SMTP服务（见文档）</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="jojo-card p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="jojo-title text-2xl">资金管理（同花顺模式）</h2>
          <button
            onClick={handleUpdateCapital}
            className="jojo-button"
          >
            更新资金
          </button>
        </div>
        
        {/* 总资产 */}
        <div className="mb-4">
          <p className="text-gray-400 text-sm mb-1">总资产</p>
          <div className="text-4xl font-bold text-jojo-gold">
            ¥{capitalInfo.total_assets.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        {/* 可用资金和持仓市值 */}
        <div className="grid grid-cols-2 gap-4 mb-6 p-4 bg-jojo-purple/30 rounded-lg border border-jojo-gold/20">
          <div>
            <p className="text-gray-400 text-sm mb-1">💰 可用资金</p>
            <p className="text-2xl font-bold text-green-400">
              ¥{capitalInfo.available_funds.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
            <p className="text-xs text-gray-400 mt-1">可用于开新仓</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm mb-1">📊 持仓市值</p>
            <p className="text-2xl font-bold text-blue-400">
              ¥{capitalInfo.position_value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
            <p className="text-xs text-gray-400 mt-1">所有持仓股票市值</p>
          </div>
        </div>

        <h3 className="text-xl font-semibold mb-4 text-jojo-gold">资金曲线</h3>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={history}>
            <CartesianGrid strokeDasharray="3 3" stroke="#FFD700" opacity={0.3} />
            <XAxis dataKey="date" stroke="#FFD700" style={{ fill: '#FFD700' }} />
            <YAxis stroke="#FFD700" style={{ fill: '#FFD700' }} />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#1a1a2e', 
                border: '2px solid #FFD700',
                borderRadius: '8px',
                color: '#FFD700'
              }}
            />
            <Legend wrapperStyle={{ color: '#FFD700' }} />
            <Line 
              type="monotone" 
              dataKey="capital" 
              stroke="#FFD700" 
              strokeWidth={3}
              dot={{ fill: '#FFD700', r: 4 }}
              activeDot={{ r: 6 }}
              name="总资产"
            />
            <Line 
              type="monotone" 
              dataKey="available_funds" 
              stroke="#10B981" 
              strokeWidth={2}
              dot={{ fill: '#10B981', r: 3 }}
              name="可用资金"
            />
            <Line 
              type="monotone" 
              dataKey="position_value" 
              stroke="#3B82F6" 
              strokeWidth={2}
              dot={{ fill: '#3B82F6', r: 3 }}
              name="持仓市值"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
      
    {/* JOJO风格弹窗 */}
    <Modal />
    <CapitalModal />
    </>
  );
}
