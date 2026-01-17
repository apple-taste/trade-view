import { useEffect, useState } from 'react';
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, eachDayOfInterval, isSameMonth, isSameDay, addMonths, subMonths } from 'date-fns';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import axios from 'axios';
import { useTrade } from '../../contexts/TradeContext';

interface CalendarPanelProps {
  selectedDate: string;
  onDateChange: (date: string) => void;
  apiBase?: string; // 默认 /api/trades，可传 /api/forex/trades
  refreshKey?: number;
}

export default function CalendarPanel({ selectedDate, onDateChange, apiBase = '/api/trades', refreshKey }: CalendarPanelProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date(selectedDate));
  const [tradeDates, setTradeDates] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const { _calendarRefreshKey, effectiveStrategyId, effectiveForexStrategyId } = useTrade();
  const selectedStrategyId = apiBase === '/api/forex/trades' ? effectiveForexStrategyId : effectiveStrategyId;

  useEffect(() => {
    fetchTradeDates();
  }, [_calendarRefreshKey, refreshKey, apiBase, selectedStrategyId]); // 当refresh key变化时刷新

  useEffect(() => {
    // 当selectedDate改变时，更新currentMonth
    setCurrentMonth(new Date(selectedDate));
  }, [selectedDate]);

  const fetchTradeDates = async () => {
    setLoading(true);
    try {
      if (selectedStrategyId == null) {
        setTradeDates(new Set());
        return;
      }
      const params = { strategy_id: selectedStrategyId };
      const response = await axios.get(`${apiBase}/dates`, { params });
      setTradeDates(new Set(response.data));
    } catch (error) {
      console.error('获取交易日期失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(currentMonth);
  const calendarStart = startOfWeek(monthStart, { weekStartsOn: 1 }); // 周一开始
  const calendarEnd = endOfWeek(monthEnd, { weekStartsOn: 1 });

  const days = eachDayOfInterval({ start: calendarStart, end: calendarEnd });

  const handleDateClick = (date: Date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    onDateChange(dateStr);
  };

  const handlePrevMonth = () => {
    setCurrentMonth(subMonths(currentMonth, 1));
  };

  const handleNextMonth = () => {
    setCurrentMonth(addMonths(currentMonth, 1));
  };

  const handleToday = () => {
    const today = new Date();
    setCurrentMonth(today);
    handleDateClick(today);
  };

  const isTradeDate = (date: Date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    return tradeDates.has(dateStr);
  };

  const isSelected = (date: Date) => {
    return isSameDay(date, new Date(selectedDate));
  };

  const isToday = (date: Date) => {
    return isSameDay(date, new Date());
  };

  // 根据交易数量返回不同的表情
  const getTradeEmoji = (_date: Date) => {
    // 这里可以根据交易数量返回不同表情，目前简单返回一个
    return '📈'; // 可以用 📊 📈 💰 🎯 等
  };

  if (loading) {
    return (
      <div className="jojo-card p-6 text-center">
        <div className="text-jojo-gold animate-jojo-pulse">加载中...</div>
      </div>
    );
  }

  return (
    <div className="jojo-card p-3 h-full flex flex-col">
      {/* 月份导航 */}
      <div className="flex items-center justify-between mb-2 flex-none">
        <button
          onClick={handlePrevMonth}
          className="jojo-button p-1"
        >
          <ChevronLeft size={16} />
        </button>
        <div className="text-center">
          <h2 className="jojo-title text-sm">
            {format(currentMonth, 'yyyy年MM月')}
          </h2>
          <button
            onClick={handleToday}
            className="text-xs text-jojo-gold hover:text-jojo-gold-dark mt-0.5"
          >
            今天
          </button>
        </div>
        <button
          onClick={handleNextMonth}
          className="jojo-button p-1"
        >
          <ChevronRight size={16} />
        </button>
      </div>

      {/* 星期标题 */}
      <div className="grid grid-cols-7 gap-0.5 mb-1 flex-none">
        {['一', '二', '三', '四', '五', '六', '日'].map((day, index) => (
          <div
            key={index}
            className="text-center text-xs font-bold text-jojo-gold py-1"
          >
            {day}
          </div>
        ))}
      </div>

      {/* 日期网格 - 填充剩余空间 */}
      <div className="grid grid-cols-7 gap-0.5 flex-grow auto-rows-fr min-h-0">
        {days.map((day, index) => {
          const isCurrentMonth = isSameMonth(day, currentMonth);
          const hasTrade = isTradeDate(day);
          const isSelectedDate = isSelected(day);
          const isTodayDate = isToday(day);

          return (
            <button
              key={index}
              onClick={() => handleDateClick(day)}
              className={`
                relative p-1 rounded transition-all duration-200 flex flex-col items-center justify-center
                ${!isCurrentMonth ? 'text-gray-600 opacity-50' : 'text-white'}
                ${isSelectedDate 
                  ? 'bg-jojo-gold text-jojo-blue font-bold scale-105 shadow-lg' 
                  : 'hover:bg-jojo-blue-light'
                }
                ${isTodayDate && !isSelectedDate 
                  ? 'border border-jojo-gold' 
                  : ''
                }
              `}
            >
              <span className="block text-sm font-semibold mb-1">{format(day, 'd')}</span>
              {hasTrade && (
                <span className="text-sm animate-bounce" title="有交易记录">
                  {getTradeEmoji(day)}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* 底部信息栏 */}
      <div className="flex-none mt-2 flex items-center justify-between">
         {/* 选中日期信息 */}
         <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-400">已选:</span>
            <span className="text-sm font-bold text-jojo-gold">
              {format(new Date(selectedDate), 'yyyy-MM-dd')}
            </span>
            {isTradeDate(new Date(selectedDate)) && (
              <span className="text-xs bg-jojo-blue-light px-1.5 py-0.5 rounded text-jojo-gold flex items-center">
                <span className="mr-1">📈</span>有交易
              </span>
            )}
         </div>
         
         {/* 简易图例 */}
         <div className="flex items-center space-x-2 text-xs text-gray-400">
            <div className="flex items-center space-x-1">
               <span className="text-xs">📈</span>
               <span>交易日</span>
            </div>
            <div className="flex items-center space-x-1">
               <div className="w-1.5 h-1.5 border border-jojo-gold rounded-full"></div>
               <span>今天</span>
            </div>
         </div>
      </div>
    </div>
  );
}
