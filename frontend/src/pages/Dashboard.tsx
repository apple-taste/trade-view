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
    <div className="min-h-screen p-2 space-y-2 overflow-hidden">
      {/* 价格提醒面板 - 固定在顶部 */}
      {alerts.length > 0 && (
        <AlertPanel
          alerts={alerts}
          onDismiss={dismissAlert}
          onClearAll={clearAllAlerts}
        />
      )}

      {/* 顶部导航栏 */}
      <nav className="jojo-card p-2">
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

      {/* 顶部区域：账户 + 资金曲线 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-2">
        {/* 左侧：账户面板 */}
        <div className="lg:col-span-1">
          <UserPanel compact={true} />
        </div>
        {/* 右侧：资金成长曲线 */}
        <div className="lg:col-span-2">
          <UserPanel showChart={true} />
        </div>
      </div>

      {/* 中间区域：持仓 + 日历 + 交易历史 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-2">
        {/* 左侧：持仓面板 - 增加空间 */}
        <div className="lg:col-span-5">
          <PositionPanel />
        </div>
        {/* 中间：日历面板 - 减少空间 */}
        <div className="lg:col-span-2">
          <CalendarPanel selectedDate={selectedDate} onDateChange={setSelectedDate} />
        </div>
        {/* 右侧：交易历史面板 - 增加空间 */}
        <div className="lg:col-span-5">
          <TradeHistoryPanel selectedDate={selectedDate} />
        </div>
      </div>

      {/* 底部区域：AI分析 */}
      <div>
        <AnalysisPanel />
      </div>
    </div>
  );
}
