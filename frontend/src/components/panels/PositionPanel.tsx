import { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { Bell, BellOff, TrendingUp, TrendingDown, RefreshCw, Info } from 'lucide-react';
import { useTrade } from '../../contexts/TradeContext';
import { useAlerts } from '../../contexts/AlertContext';
import { useJojoPriceModal } from '../JojoPriceModal';

interface Position {
  id: number;
  stock_code: string;
  stock_name?: string;
  shares: number;
  buy_price: number;
  commission?: number; // 手续费
  current_price?: number;
  price_source?: string; // 价格来源
  stop_loss_price?: number;
  take_profit_price?: number;
  stop_loss_alert: boolean;
  take_profit_alert: boolean;
  holding_days: number;
}

export default function PositionPanel() {
  const { openModal: openPriceModal, Modal: PriceModal } = useJojoPriceModal();
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const refreshIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const alertedPositionsRef = useRef<Set<string>>(new Set()); // 记录已提醒的持仓，避免重复提醒
  const { refreshCalendar, refreshAnalysis, refreshUserPanel, refreshTradeHistory, _positionsRefreshKey } = useTrade();
  const { addAlert, clearAlertsByStockCode } = useAlerts();

  useEffect(() => {
    fetchPositions();
    
    // 设置定时刷新价格（每500ms，毫秒级实时性）
    refreshIntervalRef.current = setInterval(() => {
      refreshPrices(true); // 强制刷新
    }, 500); // 500ms = 0.5秒

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [_positionsRefreshKey]); // 当refresh key变化时刷新

  const fetchPositions = async () => {
    try {
      const response = await axios.get('/api/positions');
      const newPositions = response.data;
      
      // 清除已删除持仓的提醒标记
      const currentPositionIds = new Set(newPositions.map((p: Position) => p.id));
      alertedPositionsRef.current.forEach(key => {
        const positionId = parseInt(key.split('-')[0]);
        if (!currentPositionIds.has(positionId)) {
          // 该持仓已被删除，清除提醒标记
          alertedPositionsRef.current.delete(key);
        }
      });
      
      setPositions(newPositions);
      newPositions.forEach((pos: Position) => {
        if (pos.current_price) {
          checkAlerts(pos);
        }
      });
    } catch (error) {
      console.error('获取持仓失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const refreshPrices = async (forceRefresh: boolean = true) => {
    if (positions.length === 0) return;
    
    try {
      setRefreshing(true);
      const stockCodes = positions.map(p => p.stock_code);
      const response = await axios.post('/api/price/batch', stockCodes, {
        params: { force_refresh: forceRefresh }
      });
      
      // 更新价格和来源
      const priceMap = new Map<string, { price: number; source: string }>(
        response.data.map((p: any) => [
          p.stock_code,
          { price: p.price, source: p.source }
        ])
      );
      
      setPositions(prev => prev.map(pos => {
        const priceInfo = priceMap.get(pos.stock_code);
        if (priceInfo) {
          const updatedPos = {
            ...pos,
            current_price: priceInfo.price,
            price_source: priceInfo.source
          };
          // 检查提醒
          checkAlerts(updatedPos);
          return updatedPos;
        }
        return pos;
      }));
    } catch (error) {
      console.error('刷新价格失败:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const checkAlerts = (position: Position) => {
    if (!position.current_price) return;

    // 检查止损提醒
    if (position.stop_loss_alert && position.stop_loss_price) {
      if (position.current_price <= position.stop_loss_price) {
        const stopLossKey = `${position.id}-stop_loss`;
        if (!alertedPositionsRef.current.has(stopLossKey)) {
          addAlert({
            type: 'stop_loss',
            stockCode: position.stock_code,
            stockName: position.stock_name,
            currentPrice: position.current_price,
            targetPrice: position.stop_loss_price,
          });
          alertedPositionsRef.current.add(stopLossKey);
        }
      } else {
        // 价格回升，移除提醒标记（允许再次提醒）
        const stopLossKey = `${position.id}-stop_loss`;
        alertedPositionsRef.current.delete(stopLossKey);
      }
    }

    // 检查止盈提醒
    if (position.take_profit_alert && position.take_profit_price) {
      if (position.current_price >= position.take_profit_price) {
        const takeProfitKey = `${position.id}-take_profit`;
        if (!alertedPositionsRef.current.has(takeProfitKey)) {
          addAlert({
            type: 'take_profit',
            stockCode: position.stock_code,
            stockName: position.stock_name,
            currentPrice: position.current_price,
            targetPrice: position.take_profit_price,
          });
          alertedPositionsRef.current.add(takeProfitKey);
        }
      } else {
        // 价格回落，移除提醒标记（允许再次提醒）
        const takeProfitKey = `${position.id}-take_profit`;
        alertedPositionsRef.current.delete(takeProfitKey);
      }
    }
  };

  const handleToggleAlert = async (positionId: number, type: 'stop_loss' | 'take_profit', currentValue: boolean) => {
    try {
      const updateData: any = {};
      if (type === 'stop_loss') {
        updateData.stop_loss_alert = !currentValue;
      } else {
        updateData.take_profit_alert = !currentValue;
      }
      
      await axios.put(`/api/positions/${positionId}`, updateData);
      fetchPositions();
    } catch (error) {
      alert('更新失败');
    }
  };

  const handleTakeProfit = async (position: Position) => {
    const result = await openPriceModal(
      'take_profit',
      position.stock_code,
      position.stock_name,
      position.current_price,
      position.take_profit_price
    );
    if (result && result.price && !isNaN(parseFloat(result.price))) {
      try {
        const requestData: any = {
          sell_price: parseFloat(result.price)
        };
        // 如果提供了日期，添加到请求中
        if (result.date) {
          requestData.close_date = result.date;
        }
        await axios.post(`/api/positions/${position.id}/take-profit`, requestData);
        
        // 清除该股票的所有价格提醒（平仓后不再需要提醒）
        clearAlertsByStockCode(position.stock_code);
        
        fetchPositions();
        // 刷新相关面板
        refreshCalendar(); // 刷新日历标记
        refreshAnalysis(); // 刷新AI分析
        refreshUserPanel(); // 刷新用户面板（资金变化）
        refreshTradeHistory(); // 刷新开仓历史面板（显示平仓状态）
      } catch (error: any) {
        alert(error.response?.data?.detail || '操作失败');
      }
    }
  };

  const handleStopLoss = async (position: Position) => {
    const result = await openPriceModal(
      'stop_loss',
      position.stock_code,
      position.stock_name,
      position.current_price,
      position.stop_loss_price
    );
    if (result && result.price && !isNaN(parseFloat(result.price))) {
      try {
        const requestData: any = {
          sell_price: parseFloat(result.price)
        };
        // 如果提供了日期，添加到请求中
        if (result.date) {
          requestData.close_date = result.date;
        }
        await axios.post(`/api/positions/${position.id}/stop-loss`, requestData);
        
        // 清除该股票的所有价格提醒（平仓后不再需要提醒）
        clearAlertsByStockCode(position.stock_code);
        
        fetchPositions();
        // 刷新相关面板
        refreshCalendar(); // 刷新日历标记
        refreshAnalysis(); // 刷新AI分析
        refreshUserPanel(); // 刷新用户面板（资金变化）
        refreshTradeHistory(); // 刷新开仓历史面板（显示平仓状态）
      } catch (error: any) {
        alert(error.response?.data?.detail || '操作失败');
      }
    }
  };

  const calculateProfit = (position: Position) => {
    if (!position.current_price) return null;
    // 盈亏计算：(当前价格 - 买入价格) * 手数 - 手续费
    const profit = (position.current_price - position.buy_price) * position.shares - (position.commission || 0);
    return profit;
  };

  if (loading) {
    return (
      <div className="jojo-card p-6 text-center">
        <div className="text-jojo-gold animate-jojo-pulse">加载中...</div>
      </div>
    );
  }

  return (
    <div className="jojo-card p-3">
      <div className="flex justify-between items-center mb-2">
        <h2 className="jojo-title text-lg">持仓</h2>
        <button
          onClick={() => refreshPrices(true)}
          disabled={refreshing}
          className="jojo-button flex items-center space-x-1 p-1 text-xs"
          title="手动刷新价格"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          <span>刷新</span>
        </button>
      </div>

      {positions.length === 0 ? (
        <div className="text-center py-4 text-gray-400 text-sm">
          当前无持仓
        </div>
      ) : (
        <div className="space-y-2 max-h-[500px] overflow-y-auto custom-scrollbar">
          {positions.map((position) => {
            const profit = calculateProfit(position);
            const profitPercent = profit ? ((position.current_price! - position.buy_price) / position.buy_price * 100) : null;

            return (
              <div key={position.id} className="border border-jojo-gold rounded p-2 bg-jojo-blue-light">
                {/* 股票信息 */}
                <div className="mb-2">
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-bold text-jojo-gold text-sm">
                      {position.stock_code}
                      {position.stock_name && <span className="text-white"> - {position.stock_name}</span>}
                    </div>
                    {profit !== null && (
                      <div className={`text-right ${profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        <div className="text-sm font-bold">
                          {profit >= 0 ? '+' : ''}{profit.toFixed(2)} 元
                        </div>
                        <div className="text-xs">
                          {profitPercent !== null && (profitPercent >= 0 ? '+' : '')}{profitPercent?.toFixed(2)}%
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="grid grid-cols-2 gap-1 text-xs text-gray-300 mb-1">
                    <div>
                      <span className="text-gray-400">持仓天数:</span> {position.holding_days} 天
                    </div>
                    <div>
                      <span className="text-gray-400">股数:</span> {position.shares}
                    </div>
                    <div>
                      <span className="text-gray-400">买入价:</span> ¥{position.buy_price.toFixed(2)}
                    </div>
                    <div>
                      <span className="text-gray-400">市值:</span> {position.current_price ? `¥${(position.current_price * position.shares).toFixed(2)}` : '获取中...'}
                    </div>
                  </div>

                  {/* 当前市场价格 */}
                  <div className="mt-1 p-1 bg-jojo-blue rounded border border-jojo-gold">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-xs text-gray-300">当前市价:</span>
                        <span className="ml-1 font-bold text-jojo-gold text-sm">
                          {position.current_price ? `¥${position.current_price.toFixed(2)}` : '获取中...'}
                        </span>
                      </div>
                      {position.price_source && (
                        <div className="flex items-center space-x-1 text-xs text-gray-400" title={`价格来源: ${position.price_source}`}>
                          <Info size={10} />
                          <span>{position.price_source}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* 止损止盈设置 */}
                <div className="grid grid-cols-2 gap-2 mb-2">
                  {/* 止损 */}
                  <div className={`p-1.5 rounded border ${
                    position.stop_loss_alert ? 'border-red-400 bg-red-500/20' : 'border-gray-600 bg-gray-500/10'
                  }`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-gray-300">止损价格</span>
                      <button
                        onClick={() => handleToggleAlert(position.id, 'stop_loss', position.stop_loss_alert)}
                        className={`p-0.5 rounded transition-all ${
                          position.stop_loss_alert 
                            ? 'text-red-400 animate-pulse' 
                            : 'text-gray-500 hover:text-gray-300'
                        }`}
                        title={position.stop_loss_alert ? '关闭止损提醒' : '开启止损提醒'}
                      >
                        {position.stop_loss_alert ? <Bell size={12} /> : <BellOff size={12} />}
                      </button>
                    </div>
                    <div className="text-sm font-bold text-white">
                      {position.stop_loss_price ? `¥${position.stop_loss_price.toFixed(2)}` : '未设置'}
                    </div>
                    {position.stop_loss_alert && (
                      <div className="text-xs text-red-400 mt-0.5">🔔 提醒已开启</div>
                    )}
                  </div>

                  {/* 止盈 */}
                  <div className={`p-1.5 rounded border ${
                    position.take_profit_alert ? 'border-green-400 bg-green-500/20' : 'border-gray-600 bg-gray-500/10'
                  }`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-gray-300">止盈价格</span>
                      <button
                        onClick={() => handleToggleAlert(position.id, 'take_profit', position.take_profit_alert)}
                        className={`p-0.5 rounded transition-all ${
                          position.take_profit_alert 
                            ? 'text-green-400 animate-pulse' 
                            : 'text-gray-500 hover:text-gray-300'
                        }`}
                        title={position.take_profit_alert ? '关闭止盈提醒' : '开启止盈提醒'}
                      >
                        {position.take_profit_alert ? <Bell size={12} /> : <BellOff size={12} />}
                      </button>
                    </div>
                    <div className="text-sm font-bold text-white">
                      {position.take_profit_price ? `¥${position.take_profit_price.toFixed(2)}` : '未设置'}
                    </div>
                    {position.take_profit_alert && (
                      <div className="text-xs text-green-400 mt-0.5">🔔 提醒已开启</div>
                    )}
                  </div>
                </div>

                {/* 操作按钮 */}
                <div className="flex space-x-1">
                  <button
                    onClick={() => handleStopLoss(position)}
                    className="jojo-button-danger flex-1 flex items-center justify-center space-x-1 text-xs py-1"
                  >
                    <TrendingDown size={12} />
                    <span>止损</span>
                  </button>
                  <button
                    onClick={() => handleTakeProfit(position)}
                    className="jojo-button flex-1 flex items-center justify-center space-x-1 text-xs py-1"
                  >
                    <TrendingUp size={12} />
                    <span>止盈</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
      
      {refreshing && (
        <div className="mt-4 text-center text-sm text-jojo-gold">
          正在刷新价格...
        </div>
      )}
      
      {/* JOJO风格弹窗 */}
      <PriceModal />
    </div>
  );
}
