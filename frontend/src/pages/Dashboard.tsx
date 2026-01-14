import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useAlerts } from '../contexts/AlertContext';
import UserPanel from '../components/panels/UserPanel';
import CalendarPanel from '../components/panels/CalendarPanel';
import TradeHistoryPanel from '../components/panels/TradeHistoryPanel';
import PositionPanel from '../components/panels/PositionPanel';
import AnalysisPanel from '../components/panels/AnalysisPanel';
import AlertPanel from '../components/panels/AlertPanel';
import { LogOut } from 'lucide-react';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const { alerts, dismissAlert, clearAllAlerts } = useAlerts();
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  return (
    <div className="h-screen p-2 flex flex-col overflow-hidden bg-gray-900">
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
          <div className="flex items-center space-x-2">
            <h1 className="jojo-title text-2xl">JOJOLAND 交易系统</h1>
            <span className="text-jojo-gold text-xs">✨ Stand Power Activated ✨</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-jojo-gold font-bold text-sm">欢迎, {user?.username}</span>
            <button
              onClick={logout}
              className="jojo-button-danger flex items-center space-x-1 text-xs px-2 py-1"
            >
              <LogOut size={14} />
              <span>退出</span>
            </button>
          </div>
        </div>
      </nav>

      {/* 主要内容区域 - 自动填充剩余高度 */}
      <div className="flex-grow grid grid-cols-1 lg:grid-cols-12 gap-2 min-h-0">
        {/* 左侧：日历 + 持仓 (同列上下排列) */}
        <div className="lg:col-span-4 h-full flex flex-col min-h-0 space-y-2 overflow-y-auto custom-scrollbar pr-1">
          <div>
            <CalendarPanel selectedDate={selectedDate} onDateChange={setSelectedDate} />
          </div>
          <div className="flex-1 min-h-0">
            <PositionPanel />
          </div>
        </div>

        {/* 右侧：其他面板 - 占据 8/12 宽度 - 可滚动 */}
        <div className="lg:col-span-8 h-full overflow-y-auto custom-scrollbar space-y-2 pr-1">
          {/* 第一行：账户 + 资金成长曲线 (高度对齐) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-2 items-stretch">
            <div className="lg:col-span-1 h-full">
              <UserPanel compact={true} />
            </div>
            <div className="lg:col-span-2 h-full">
              <UserPanel showChart={true} />
            </div>
          </div>

          {/* 第二行：交易历史 */}
          <div className="h-[800px]">
            <TradeHistoryPanel selectedDate={selectedDate} />
          </div>

          {/* 第三行：AI分析 */}
          <div>
            <AnalysisPanel />
          </div>
        </div>
      </div>
    </div>
  );
}
