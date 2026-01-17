import { useState, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useAlerts } from '../contexts/AlertContext';
import { useLocale } from '../contexts/LocaleContext';
import UserPanel from '../components/panels/UserPanel';
import CalendarPanel from '../components/panels/CalendarPanel';
import TradeHistoryPanel from '../components/panels/TradeHistoryPanel';
import PositionPanel from '../components/panels/PositionPanel';
import AnalysisPanel from '../components/panels/AnalysisPanel';
import AlertPanel from '../components/panels/AlertPanel';
import ForexDashboard from './ForexDashboard';
import { LogOut, TrendingUp, Globe, RotateCcw, Languages } from 'lucide-react';
import { Panel, PanelGroup, ImperativePanelGroupHandle } from "react-resizable-panels";
import ResizeHandle from '../components/common/ResizeHandle';

const DEFAULT_LAYOUT = {
  main: [30, 70],
  left: [30, 70],
  right: [15, 15, 70]
};

export default function Dashboard() {
  const { user, logout, billingStatus } = useAuth();
  const { alerts, dismissAlert, clearAllAlerts } = useAlerts();
  const { language, setLanguage, t } = useLocale();
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [systemMode, setSystemMode] = useState<'stock' | 'forex'>('stock');
  const [isAnalysisMinimized, setIsAnalysisMinimized] = useState(false);
  const lastAnalysisSize = useRef(70);

  const mainGroupRef = useRef<ImperativePanelGroupHandle>(null);
  const leftGroupRef = useRef<ImperativePanelGroupHandle>(null);
  const rightGroupRef = useRef<ImperativePanelGroupHandle>(null);

  // Toggle Analysis Panel Minimization
  const handleToggleAnalysis = () => {
    const group = rightGroupRef.current;
    if (!group) return;

    const layout = group.getLayout();
    if (!layout || layout.length !== 3) return;

    if (isAnalysisMinimized) {
      // Expand
      const targetSize = lastAnalysisSize.current;
      const currentSize = layout[2];
      const diff = targetSize - currentSize;
      
      // Reduce the middle panel (Trade History) to make space
      const newLayout = [...layout];
      newLayout[1] = Math.max(newLayout[1] - diff, 10); // Ensure middle panel doesn't disappear
      newLayout[2] = targetSize;
      
      // Adjust if total > 100 due to rounding or limits
      const total = newLayout.reduce((a, b) => a + b, 0);
      if (Math.abs(total - 100) > 0.1) {
          // Normalize
          const scale = 100 / total;
          newLayout.forEach((_, i) => newLayout[i] *= scale);
      }

      group.setLayout(newLayout);
      setIsAnalysisMinimized(false);
    } else {
      // Minimize
      lastAnalysisSize.current = layout[2];
      
      const minSize = 6; // Target size for minimized state
      const diff = layout[2] - minSize;
      
      const newLayout = [...layout];
      // Give space to middle panel
      newLayout[1] = newLayout[1] + diff;
      newLayout[2] = minSize;
      
      group.setLayout(newLayout);
      setIsAnalysisMinimized(true);
    }
  };

  const handleLayoutReset = () => {
    if (confirm(t('nav.confirmResetLayout'))) {
      mainGroupRef.current?.setLayout(DEFAULT_LAYOUT.main);
      leftGroupRef.current?.setLayout(DEFAULT_LAYOUT.left);
      rightGroupRef.current?.setLayout(DEFAULT_LAYOUT.right);
      
      // 清除本地存储
      localStorage.removeItem('dashboard_layout_main');
      localStorage.removeItem('dashboard_layout_left');
      localStorage.removeItem('dashboard_layout_right');
    }
  };

  const onLayoutChange = (key: string, sizes: number[]) => {
    localStorage.setItem(`dashboard_layout_${key}`, JSON.stringify(sizes));

    // 监听右侧面板组的布局变化，自动更新AI分析面板的最小化状态
    if (key === 'right' && sizes.length === 3) {
      const analysisSize = sizes[2];
      // 如果尺寸大于12%且当前是最小化状态，则自动展开
      if (analysisSize > 12 && isAnalysisMinimized) {
        setIsAnalysisMinimized(false);
      } 
      // 如果尺寸小于8%且当前是展开状态，则自动最小化
      else if (analysisSize <= 8 && !isAnalysisMinimized) {
        setIsAnalysisMinimized(true);
      }
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-900 overflow-y-auto custom-scrollbar">
      <div className="p-2 flex flex-col min-h-[1600px] h-full">
      {/* 价格提醒面板 - 固定在顶部 */}
      {alerts.length > 0 && (
        <AlertPanel
          alerts={alerts}
          onDismiss={dismissAlert}
          onClearAll={clearAllAlerts}
        />
      )}

      {/* 顶部导航栏 - 固定高度 */}
      <nav className="jojo-card p-2 mb-2 flex-none">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <h1 className="jojo-title text-2xl">{t('app.title')}</h1>
              <span className="text-jojo-gold text-xs hidden md:inline">✨ Stand Power Activated ✨</span>
            </div>
            
            {/* 系统切换器 */}
            <div className="flex bg-gray-800 rounded-lg p-1 border border-gray-700">
              <button
                onClick={() => setSystemMode('stock')}
                className={`flex items-center space-x-1 px-3 py-1 rounded-md text-sm font-bold transition-all duration-300 ${
                  systemMode === 'stock'
                    ? 'bg-jojo-gold text-gray-900 shadow-lg shadow-yellow-500/20'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <TrendingUp size={14} />
                <span>{t('nav.switchToStock')}</span>
              </button>
              <button
                onClick={() => setSystemMode('forex')}
                className={`flex items-center space-x-1 px-3 py-1 rounded-md text-sm font-bold transition-all duration-300 ${
                  systemMode === 'forex'
                    ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/20'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <Globe size={14} />
                <span>{t('nav.switchToForex')}</span>
              </button>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setLanguage(language === 'zh' ? 'en' : 'zh')}
              className="p-2 text-gray-400 hover:text-white transition-colors"
              title={language === 'zh' ? t('lang.en') : t('lang.zh')}
            >
              <Languages size={16} />
            </button>
            <button
              onClick={handleLayoutReset}
              className="p-2 text-gray-400 hover:text-white transition-colors"
              title={t('nav.resetLayout')}
            >
              <RotateCcw size={16} />
            </button>
            <div className="flex items-center gap-2 min-w-0">
              <span
                className={`px-2 py-0.5 rounded text-[11px] font-extrabold border ${
                  billingStatus?.is_paid
                    ? 'bg-jojo-gold text-gray-900 border-yellow-400'
                    : 'bg-gray-800 text-gray-200 border-gray-700'
                }`}
              >
                {billingStatus?.is_paid ? 'PRO' : 'FREE'}
              </span>
              <span className="text-jojo-gold font-bold text-sm truncate">{t('nav.welcome')}, {user?.username}</span>
            </div>
            <button
              onClick={logout}
              className="jojo-button-danger flex items-center space-x-1 text-xs px-2 py-1"
            >
              <LogOut size={14} />
              <span>{t('nav.logout')}</span>
            </button>
          </div>
        </div>
      </nav>

      {/* 主要内容区域 - 自动填充剩余高度 */}
      {systemMode === 'stock' ? (
        <div className="flex-grow flex flex-col min-h-0">
          <PanelGroup 
            direction="horizontal" 
            ref={mainGroupRef}
            onLayout={(sizes) => onLayoutChange('main', sizes)}
            autoSaveId="dashboard-main"
            style={{ height: '100%' }}
          >
            {/* 左侧：日历 + 持仓 */}
            <Panel defaultSize={30} minSize={20} className="flex flex-col pr-1">
              <PanelGroup 
                direction="vertical"
                ref={leftGroupRef}
                onLayout={(sizes) => onLayoutChange('left', sizes)}
                autoSaveId="dashboard-left-v4"
              >
                 <Panel defaultSize={30} minSize={20}>
                    <div className="h-full overflow-hidden pb-1">
                       <CalendarPanel selectedDate={selectedDate} onDateChange={setSelectedDate} />
                    </div>
                 </Panel>
                 <ResizeHandle direction="vertical" />
                 <Panel minSize={30}>
                    <div className="h-full overflow-y-auto custom-scrollbar pt-1">
                       <PositionPanel />
                    </div>
                 </Panel>
              </PanelGroup>
            </Panel>
            
            <ResizeHandle />

            {/* 右侧：其他面板 */}
            <Panel minSize={30} className="pl-1">
              <PanelGroup 
                direction="vertical"
                ref={rightGroupRef}
                onLayout={(sizes) => onLayoutChange('right', sizes)}
                autoSaveId="dashboard-right-v4"
              >
                 {/* 第一行：账户 + 资金成长曲线 */}
                 <Panel defaultSize={15} minSize={10}>
                   <div className="h-full grid grid-cols-1 lg:grid-cols-3 gap-2 pb-1 overflow-hidden">
                      <div className="lg:col-span-1 h-full overflow-hidden">
                        <UserPanel compact={true} />
                      </div>
                      <div className="lg:col-span-2 h-full overflow-hidden">
                        <UserPanel showChart={true} />
                      </div>
                   </div>
                 </Panel>
                 
                 <ResizeHandle direction="vertical" />
                 
                 {/* 第二行：交易历史 */}
                 <Panel defaultSize={15} minSize={10}>
                   <div className="h-full py-1 overflow-hidden">
                     <TradeHistoryPanel selectedDate={selectedDate} />
                   </div>
                 </Panel>

                 <ResizeHandle direction="vertical" />

                 {/* 第三行：AI分析 */}
                 <Panel defaultSize={70} minSize={6}>
                   <div className={`h-full pt-1 ${isAnalysisMinimized ? 'overflow-hidden' : 'overflow-y-auto custom-scrollbar'}`}>
                     <AnalysisPanel 
                       isMinimized={isAnalysisMinimized}
                       onToggleMinimize={handleToggleAnalysis}
                     />
                   </div>
                 </Panel>
              </PanelGroup>
            </Panel>
          </PanelGroup>
        </div>
      ) : (
        <div className="flex-grow min-h-0">
          <ForexDashboard />
        </div>
      )}
      </div>
    </div>
  );
}
