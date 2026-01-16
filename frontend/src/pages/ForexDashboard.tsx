import { useEffect, useMemo, useState } from 'react';
import { ForexProvider, useForex } from '../contexts/ForexContext';
import { useLocale } from '../contexts/LocaleContext';
import ForexSettingsModal from '../components/forex/ForexSettingsModal';
import { Settings, BarChart2, TrendingUp } from 'lucide-react';
import { Panel, PanelGroup } from "react-resizable-panels";
import ResizeHandle from '../components/common/ResizeHandle';
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend } from 'recharts';
import CalendarPanel from '../components/panels/CalendarPanel';
import JojolandMascot from '../components/JojolandMascot';
import ForexTerminal from '../components/forex/ForexTerminal';
import AnalysisPanel from '../components/panels/AnalysisPanel';
import axios from 'axios';
import { useTrade } from '../contexts/TradeContext';

type CapitalHistoryPoint = { date: string; equity: number; balance: number };

type CapitalHistoriesResponse = {
  market: string;
  baseline: number | null;
  anchor_date?: string | null;
  strategies: Array<{ id: number; name: string }>;
  series_by_strategy_id: Record<number, CapitalHistoryPoint[]>;
};

const formatDate = (d: Date) => d.toISOString().slice(0, 10);

type RangePreset = 'ALL' | '7D' | '30D' | '90D' | 'YTD' | 'CUSTOM';

const ForexDashboardContent = () => {
  const [showSettings, setShowSettings] = useState(false);
  const { account, capitalHistory, openTrades, closedTrades, refreshKey } = useForex();
  const { t } = useLocale();
  const { forexStrategies, effectiveForexStrategyId, setCurrentForexStrategyId } = useTrade();
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [isAnalysisMinimized, setIsAnalysisMinimized] = useState(false);

  const [capitalMode, setCapitalMode] = useState<'all' | 'single'>('all');
  const [rangePreset, setRangePreset] = useState<RangePreset>('ALL');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');
  const [capitalLoading, setCapitalLoading] = useState(false);
  const [capitalResponse, setCapitalResponse] = useState<CapitalHistoriesResponse | null>(null);

  const { startDate, endDate } = useMemo(() => {
    const today = new Date();
    const end = formatDate(today);

    if (rangePreset === 'ALL') return { startDate: null as string | null, endDate: null as string | null };
    if (rangePreset === 'CUSTOM') {
      return {
        startDate: customStart ? customStart : null,
        endDate: customEnd ? customEnd : null,
      };
    }
    if (rangePreset === 'YTD') {
      const start = new Date(today.getFullYear(), 0, 1);
      return { startDate: formatDate(start), endDate: end };
    }

    const days = rangePreset === '7D' ? 7 : rangePreset === '30D' ? 30 : 90;
    const start = new Date(today);
    start.setDate(today.getDate() - (days - 1));
    return { startDate: formatDate(start), endDate: end };
  }, [customEnd, customStart, rangePreset]);

  useEffect(() => {
    const fetchCapitalHistories = async () => {
      if (forexStrategies.length === 0) {
        setCapitalResponse(null);
        return;
      }
      setCapitalLoading(true);
      try {
        const params: any = { market: 'forex' };
        if (startDate) params.start_date = startDate;
        if (endDate) params.end_date = endDate;
        const res = await axios.get('/api/user/strategies/capital-histories', { params });
        setCapitalResponse(res.data as CapitalHistoriesResponse);
      } catch {
        setCapitalResponse(null);
      } finally {
        setCapitalLoading(false);
      }
    };

    fetchCapitalHistories();
  }, [endDate, forexStrategies.length, refreshKey, startDate]);

  const singleStrategySeries = useMemo(() => {
    if (!capitalResponse) return [];
    if (effectiveForexStrategyId == null) return [];
    return capitalResponse.series_by_strategy_id?.[effectiveForexStrategyId] ?? [];
  }, [capitalResponse, effectiveForexStrategyId]);

  const singleChartData = useMemo(() => {
    const source = singleStrategySeries.length > 0 ? singleStrategySeries : (capitalHistory ?? []);
    return (source ?? []).map((p: any) => ({
      date: String(p.date),
      equity: Number(p.equity ?? 0),
      balance: Number(p.balance ?? 0),
    }));
  }, [capitalHistory, singleStrategySeries]);

  const allChart = useMemo(() => {
    const response = capitalResponse;
    if (!response) return { data: [] as any[], keysByStrategyId: new Map<number, string>() };

    const ids = forexStrategies.map((s) => s.id);
    const keysByStrategyId = new Map<number, string>();
    for (const id of ids) keysByStrategyId.set(id, `s_${id}`);

    const dateSet = new Set<string>();
    for (const id of ids) {
      const series = response.series_by_strategy_id?.[id] ?? [];
      for (const p of series) dateSet.add(p.date);
    }
    const dates = Array.from(dateSet).sort();

    const valueByStrategyIdByDate = new Map<number, Map<string, number>>();
    for (const id of ids) {
      const m = new Map<string, number>();
      for (const p of response.series_by_strategy_id?.[id] ?? []) {
        m.set(p.date, Number(p.equity ?? 0));
      }
      valueByStrategyIdByDate.set(id, m);
    }

    const data = dates.map((d) => {
      const row: any = { date: d };
      for (const id of ids) {
        const key = keysByStrategyId.get(id)!;
        const v = valueByStrategyIdByDate.get(id)?.get(d);
        row[key] = v != null ? v : null;
      }
      return row;
    });

    return { data, keysByStrategyId };
  }, [capitalResponse, forexStrategies]);

  const lineColors = [
    '#FFD700', // Gold
    '#10B981', // Emerald
    '#3B82F6', // Blue
    '#EC4899', // Pink
    '#8B5CF6', // Violet
    '#F97316', // Orange
    '#EF4444', // Red
    '#14B8A6', // Teal
    '#F59E0B', // Amber
    '#6366F1', // Indigo
    '#A855F7', // Purple
    '#06B6D4', // Cyan
  ];

  return (
    <div className="h-full flex flex-col space-y-2 overflow-hidden text-gray-200 p-2 relative">
      <div className="absolute top-0 right-14 text-[10px] text-gray-600 opacity-50 z-50">v1.1.3</div>
      {/* Top Bar: Title & Settings */}
      <div className="flex justify-between items-center bg-gray-800 p-2 rounded-lg border border-gray-700 flex-none">
        <div className="flex items-center gap-4 min-w-0">
            <div className="flex items-center gap-2">
                <BarChart2 className="text-blue-500" />
                <h2 className="font-bold text-lg">{t('forex.title')}</h2>
            </div>
            <div className="hidden md:flex gap-4 text-sm">
                <div>
                    <span className="text-gray-500 mr-1">{t('forex.balance')}:</span>
                    <span className="font-mono font-bold">{account.balance.toFixed(2)}</span>
                </div>
                <div>
                    <span className="text-gray-500 mr-1">{t('forex.equity')}:</span>
                    <span className="font-mono font-bold text-blue-400">{account.equity.toFixed(2)}</span>
                </div>
            </div>
        </div>
        <div className="hidden xl:flex flex-1 justify-center px-2 min-w-0">
          <JojolandMascot inline />
        </div>
        <button
          onClick={() => setShowSettings(true)}
          className="p-2 hover:bg-gray-700 rounded-full transition-colors text-gray-400 hover:text-white"
          title={t('forex.brokerSettings')}
        >
          <Settings size={20} />
        </button>
      </div>

      {/* Main Workspace */}
      <div className="flex-grow min-h-0">
        <PanelGroup direction="vertical">
          {/* 第一行：账户概览 + 资金曲线（A股同款“资金管理”视图） */}
          <Panel defaultSize={30} minSize={18}>
            <div className="h-full grid grid-cols-1 lg:grid-cols-3 gap-2 pb-1 overflow-hidden">
              {/* 账户概览 */}
              <div className="lg:col-span-1 h-full overflow-hidden">
                <div className="h-full bg-gray-800 rounded-lg border border-gray-700 p-3 flex flex-col">
                  <h3 className="text-lg font-bold text-jojo-gold mb-2">账户与资金</h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-gray-900 rounded border border-gray-700">
                      <p className="text-xs text-gray-400 mb-1">{t('forex.balance')}</p>
                      <p className="text-2xl font-bold text-gray-200">{account.balance.toFixed(2)}</p>
                    </div>
                    <div className="p-3 bg-gray-900 rounded border border-gray-700">
                      <p className="text-xs text-gray-400 mb-1">{t('forex.equity')}</p>
                      <p className="text-2xl font-bold text-blue-400">{account.equity.toFixed(2)}</p>
                    </div>
                    <div className="p-3 bg-gray-900 rounded border border-gray-700">
                      <p className="text-xs text-gray-400 mb-1">{t('forex.freeMargin')}</p>
                      <p className="text-2xl font-bold text-green-400">{account.freeMargin.toFixed(2)}</p>
                    </div>
                    <div className="p-3 bg-gray-900 rounded border border-gray-700">
                      <p className="text-xs text-gray-400 mb-1">{t('forex.marginLevel')}</p>
                      <p className={`text-2xl font-bold ${account.marginLevel < 100 ? 'text-red-500' : 'text-green-500'}`}>
                        {account.marginLevel.toFixed(2)}%
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 text-right text-xs text-gray-500">
                    {t('forex.maxDrawdown')}: <span className="font-mono">{account.maxDrawdown.toFixed(2)}%</span>
                  </div>
                </div>
              </div>

              {/* 资金曲线（净值+余额） */}
              <div className="lg:col-span-2 h-full overflow-hidden">
                <div className="h-full bg-gray-800 rounded-lg border border-gray-700 p-3">
                  <div className="flex items-center justify-between gap-2 mb-2 text-gray-400">
                    <div className="flex items-center gap-2">
                      <TrendingUp size={16} /> <span className="font-bold">资金成长曲线</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <select
                        value={capitalMode === 'all' ? 'ALL' : (effectiveForexStrategyId ?? '')}
                        onChange={(e) => {
                          const v = e.target.value;
                          if (v === 'ALL') {
                            setCapitalMode('all');
                            return;
                          }
                          const id = v ? Number(v) : null;
                          if (id != null) {
                            setCapitalMode('single');
                            setCurrentForexStrategyId(id);
                          }
                        }}
                        className="px-3 py-1 text-xs font-bold rounded bg-gray-900 border border-jojo-gold text-jojo-gold focus:outline-none"
                      >
                        <option value="ALL">全部策略</option>
                        {forexStrategies.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name}
                          </option>
                        ))}
                      </select>
                      <select
                        value={rangePreset}
                        onChange={(e) => setRangePreset(e.target.value as RangePreset)}
                        className="px-3 py-1 text-xs font-bold rounded bg-gray-900 border border-jojo-gold text-jojo-gold focus:outline-none"
                      >
                        <option value="ALL">全部</option>
                        <option value="7D">近7天</option>
                        <option value="30D">近30天</option>
                        <option value="90D">近90天</option>
                        <option value="YTD">今年</option>
                        <option value="CUSTOM">自定义</option>
                      </select>
                    </div>
                  </div>
                  {rangePreset === 'CUSTOM' && (
                    <div className="mb-2 flex items-center gap-2 text-xs">
                      <input
                        type="date"
                        value={customStart}
                        onChange={(e) => setCustomStart(e.target.value)}
                        className="px-2 py-1 rounded bg-gray-900 border border-gray-700 text-gray-200 focus:outline-none"
                      />
                      <span className="text-gray-500">至</span>
                      <input
                        type="date"
                        value={customEnd}
                        onChange={(e) => setCustomEnd(e.target.value)}
                        className="px-2 py-1 rounded bg-gray-900 border border-gray-700 text-gray-200 focus:outline-none"
                      />
                    </div>
                  )}
                  <div className="h-[340px] md:h-full min-h-[340px]">
                    {capitalLoading ? (
                      <div className="h-full flex items-center justify-center text-gray-600 text-xs">加载中...</div>
                    ) : capitalMode === 'all' ? (
                      allChart.data.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={allChart.data} margin={{ top: 10, right: 10, left: 0, bottom: 30 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="date" stroke="#9CA3AF" fontSize={12} height={40} tickMargin={10} />
                            <YAxis stroke="#9CA3AF" fontSize={12} />
                            <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', color: '#e5e7eb' }} />
                            <Legend verticalAlign="top" height={24} />
                            {forexStrategies.map((s, idx) => {
                              const key = allChart.keysByStrategyId.get(s.id);
                              if (!key) return null;
                              return (
                                <Line
                                  key={s.id}
                                  type="monotone"
                                  dataKey={key}
                                  name={s.name}
                                  stroke={lineColors[idx % lineColors.length]}
                                  strokeWidth={2}
                                  dot={false}
                                  connectNulls
                                />
                              );
                            })}
                          </LineChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="h-full flex items-center justify-center text-gray-600 text-xs">
                          {t('forex.noData')}
                        </div>
                      )
                    ) : singleChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={singleChartData} margin={{ top: 10, right: 10, left: 0, bottom: 30 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                          <XAxis dataKey="date" stroke="#9CA3AF" fontSize={12} height={40} tickMargin={10} />
                          <YAxis stroke="#9CA3AF" fontSize={12} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', color: '#e5e7eb' }}
                          />
                          <Legend verticalAlign="top" height={24} />
                          <Line type="monotone" dataKey="equity" name={t('forex.equity')} stroke="#34d399" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="balance" name={t('forex.balance')} stroke="#60a5fa" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center text-gray-600 text-xs">
                        {t('forex.noData')}
                      </div>
                    )}
                  </div>
                  <div className="mt-3">
                    <CalendarPanel
                      selectedDate={selectedDate}
                      onDateChange={setSelectedDate}
                      apiBase="/api/forex/trades"
                      refreshKey={refreshKey}
                    />
                  </div>
                </div>
              </div>
            </div>
          </Panel>
          
          <ResizeHandle direction="vertical" />

          {/* 第二行：交易账单（A股同款“交易记录”视图，无下单/行情） */}
          <Panel defaultSize={15} minSize={12}>
            <div className="h-full pt-1">
              <div className="h-full bg-gray-800 rounded-lg border border-gray-700 flex flex-col overflow-hidden">
                <div className="p-2 bg-gray-900 border-b border-gray-700 flex items-center justify-between">
                  <h3 className="font-bold text-jojo-gold">交易记录</h3>
                  <span className="text-xs text-gray-500">
                    共 {openTrades.length + closedTrades.length} 条（含持仓与已平仓）
                  </span>
                </div>
                <div className="flex-1 overflow-hidden">
                  <ForexTerminal />
                </div>
              </div>
            </div>
          </Panel>

          <ResizeHandle direction="vertical" />

          <Panel defaultSize={55} minSize={10}>
            <div className={`h-full pt-1 ${isAnalysisMinimized ? 'overflow-hidden' : 'overflow-y-auto custom-scrollbar'}`}>
              <AnalysisPanel
                isMinimized={isAnalysisMinimized}
                onToggleMinimize={() => setIsAnalysisMinimized((v) => !v)}
                systemMode="forex"
                refreshKey={refreshKey}
              />
            </div>
          </Panel>
        </PanelGroup>
      </div>

      {/* Modals */}
      {showSettings && <ForexSettingsModal onClose={() => setShowSettings(false)} />}
    </div>
  );
};

export default function ForexDashboard() {
  return (
    <ForexProvider>
      <ForexDashboardContent />
    </ForexProvider>
  );
}
