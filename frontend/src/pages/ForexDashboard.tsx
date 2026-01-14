import { useState, useMemo } from 'react';
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

const ForexDashboardContent = () => {
  const [showSettings, setShowSettings] = useState(false);
  const { account, capitalHistory, openTrades, closedTrades, refreshKey } = useForex();
  const { t } = useLocale();
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [isAnalysisMinimized, setIsAnalysisMinimized] = useState(false);

  const chartData = useMemo(() => {
    return (capitalHistory ?? []).map((p) => ({
      date: p.date,
      equity: p.equity,
      balance: p.balance,
    }));
  }, [capitalHistory]);

  return (
    <div className="h-full flex flex-col space-y-2 overflow-hidden text-gray-200 p-2">
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
                  <div className="flex items-center gap-2 mb-2 text-gray-400">
                    <TrendingUp size={16} /> <span className="font-bold">资金曲线</span>
                  </div>
                  <div className="h-[340px] md:h-full min-h-[340px]">
                    {chartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 30 }}>
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
