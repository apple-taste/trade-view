import { useEffect, useMemo, useState, useRef } from 'react';
import axios from 'axios';
import { Bell, BellOff, TrendingUp, TrendingDown, RefreshCw, Info } from 'lucide-react';
import { useTrade } from '../../contexts/TradeContext';
import { useAlerts } from '../../contexts/AlertContext';
import { useJojoPriceModal } from '../JojoPriceModal';
import { perfMonitor } from '../../utils/performance';

interface PartialCloseRecord {
  id: number;
  close_time?: string;
  shares: number;
  sell_price?: number;
  order_result?: string;
  profit_loss?: number;
  commission?: number;
}

interface Position {
  id: number;
  stock_code: string;
  stock_name?: string;
  shares: number;
  opened_shares?: number;
  closed_shares?: number;
  partial_closes?: PartialCloseRecord[];
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
  const [isSyncing, setIsSyncing] = useState(false);
  const refreshIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const autoRefreshingRef = useRef(false);
  const alertedPositionsRef = useRef<Set<string>>(new Set()); // 记录已提醒的持仓，避免重复提醒
  const panelRef = useRef<HTMLDivElement>(null);
  const { 
    refreshCalendar, 
    refreshAnalysis, 
    refreshUserPanel, 
    refreshTradeHistory, 
    _positionsRefreshKey, 
    effectiveStrategyId,
    lastAddedTrade, 
    setLastAddedTrade,
    lastUpdatedTrade,
    setLastUpdatedTrade,
    lastDeletedTradeId,
    setLastDeletedTradeId
  } = useTrade();
  const { addAlert, clearAlertsByStockCode } = useAlerts();

  const formatDate = (value?: string) => {
    if (!value) return '';
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return value;
    return dt.toLocaleDateString('zh-CN');
  };

  const calc334Shares = (totalShares: number) => {
    if (!Number.isFinite(totalShares) || totalShares <= 0) return { a: 0, b: 0, c: 0 };
    const total = Math.floor(totalShares / 100) * 100;
    const aBase = Math.floor((total * 3) / 10 / 100) * 100;
    const bBase = Math.floor((total * 3) / 10 / 100) * 100;
    const cBase = Math.max(0, total - aBase - bBase);
    const c = Math.floor(cBase / 100) * 100;
    const remainder = total - (aBase + bBase + c);
    return { a: aBase, b: bBase, c: c + remainder };
  };

  // 监听新增交易，实现增量更新
  useEffect(() => {
    if (lastAddedTrade) {
      // 如果是已平仓的交易（有卖出价格或离场时间），不添加到持仓列表
      if (lastAddedTrade.sell_price || lastAddedTrade.close_time) {
        setLastAddedTrade(null);
        return;
      }

      // 检查是否已存在（避免重复添加）
      setPositions(prev => {
        if (prev.find(p => p.id === lastAddedTrade.id)) return prev;
        
        // 转换 Trade 到 Position
        // 注意：这里假设 lastAddedTrade 符合 Position 接口的部分字段，
        // 或者我们需要手动映射。由于 Trade 和 Position 结构相似，只需补充缺少的字段。
        const newPosition: Position = {
          id: lastAddedTrade.id,
          stock_code: lastAddedTrade.stock_code,
          stock_name: lastAddedTrade.stock_name,
          shares: lastAddedTrade.shares,
          opened_shares: lastAddedTrade.shares,
          closed_shares: 0,
          partial_closes: [],
          buy_price: lastAddedTrade.buy_price,
          commission: lastAddedTrade.commission,
          current_price: lastAddedTrade.current_price || lastAddedTrade.buy_price, // 初始使用买入价
          price_source: '最新交易',
          stop_loss_price: lastAddedTrade.stop_loss_price,
          take_profit_price: lastAddedTrade.take_profit_price,
          stop_loss_alert: lastAddedTrade.stop_loss_alert,
          take_profit_alert: lastAddedTrade.take_profit_alert,
          holding_days: 0
        };
        
        return [newPosition, ...prev];
      });
      
      // 消费完后重置
      setLastAddedTrade(null);
      
      // 立即触发一次价格刷新，获取最新现价
      setTimeout(() => refreshPrices(true), 100);
    }
  }, [lastAddedTrade, setLastAddedTrade]);

  // 监听编辑交易，实现增量更新
  useEffect(() => {
    if (lastUpdatedTrade) {
      // 如果更新后的交易已平仓，从持仓列表中移除
      if (lastUpdatedTrade.sell_price || lastUpdatedTrade.close_time) {
        setPositions(prev => prev.filter(p => p.id !== lastUpdatedTrade.id));
        
        // 清除提醒标记
        const stopLossKey = `${lastUpdatedTrade.id}-stop_loss`;
        const takeProfitKey = `${lastUpdatedTrade.id}-take_profit`;
        alertedPositionsRef.current.delete(stopLossKey);
        alertedPositionsRef.current.delete(takeProfitKey);
      } else {
        // 更新持仓信息
        setPositions(prev => prev.map(p => {
          if (p.id === lastUpdatedTrade.id) {
            return {
              ...p,
              stock_code: lastUpdatedTrade.stock_code,
              stock_name: lastUpdatedTrade.stock_name,
              shares: lastUpdatedTrade.shares,
              buy_price: lastUpdatedTrade.buy_price,
              stop_loss_price: lastUpdatedTrade.stop_loss_price,
              take_profit_price: lastUpdatedTrade.take_profit_price,
              stop_loss_alert: lastUpdatedTrade.stop_loss_alert,
              take_profit_alert: lastUpdatedTrade.take_profit_alert,
            };
          }
          return p;
        }));
      }
      setLastUpdatedTrade(null);
    }
  }, [lastUpdatedTrade, setLastUpdatedTrade]);

  // 监听删除交易，实现增量更新
  useEffect(() => {
    if (lastDeletedTradeId) {
      setPositions(prev => prev.filter(p => p.id !== lastDeletedTradeId));
      
      // 清除提醒标记
      const stopLossKey = `${lastDeletedTradeId}-stop_loss`;
      const takeProfitKey = `${lastDeletedTradeId}-take_profit`;
      alertedPositionsRef.current.delete(stopLossKey);
      alertedPositionsRef.current.delete(takeProfitKey);
      
      setLastDeletedTradeId(null);
    }
  }, [lastDeletedTradeId, setLastDeletedTradeId]);

  useEffect(() => {
    setLoading(true);
    fetchPositions();
    
    // 设置定时刷新价格（每500ms，毫秒级实时性）
    refreshIntervalRef.current = setInterval(() => {
      refreshPrices(true, true); // 强制刷新，但静默模式（不显示loading，不锁定高度）
    }, 500); // 500ms = 0.5秒

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [_positionsRefreshKey, effectiveStrategyId]); // 当refresh key变化时刷新

  const fetchPositions = async () => {
    setIsSyncing(true);
    try {
      if (effectiveStrategyId == null) {
        setPositions([]);
        alertedPositionsRef.current.clear();
        return;
      }
      const params = effectiveStrategyId != null ? { strategy_id: effectiveStrategyId } : undefined;
      const response = await axios.get('/api/positions', { params });
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
      perfMonitor.end('PositionPanel_FetchPositions');
      setLoading(false);
      setIsSyncing(false);
    }
  };

  const refreshPrices = async (forceRefresh: boolean = true, silent: boolean = false) => {
    if (silent) {
      if (autoRefreshingRef.current) return;
      autoRefreshingRef.current = true;
    }
    
    if (positions.length === 0) return;
    
    // 锁定面板高度以防止抖动
    if (panelRef.current && !silent) {
      const height = panelRef.current.offsetHeight;
      panelRef.current.style.minHeight = `${height}px`;
    }
    
    try {
      if (!silent) setRefreshing(true);
      if (!silent) perfMonitor.start('PositionPanel_RefreshPrices');
      
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
      
      setPositions(prev => {
        let hasChanges = false;
        const newPositions = prev.map(pos => {
          const priceInfo = priceMap.get(pos.stock_code);
          if (priceInfo) {
            // 只有当价格发生变化时才更新
            if (pos.current_price !== priceInfo.price || pos.price_source !== priceInfo.source) {
              hasChanges = true;
              const updatedPos = {
                ...pos,
                current_price: priceInfo.price,
                price_source: priceInfo.source
              };
              // 检查提醒
              checkAlerts(updatedPos);
              return updatedPos;
            }
          }
          return pos;
        });
        
        return hasChanges ? newPositions : prev;
      });
    } catch (error) {
      console.error('刷新价格失败:', error);
    } finally {
      if (!silent) setRefreshing(false);
      if (silent) {
        autoRefreshingRef.current = false;
      }
      if (panelRef.current && !silent) {
        setTimeout(() => {
          if (panelRef.current) panelRef.current.style.minHeight = '';
        }, 100);
      }
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
    // 乐观更新：先更新UI
    const originalPositions = [...positions];
    setPositions(prev => prev.map(p => {
      if (p.id === positionId) {
        return {
          ...p,
          [type === 'stop_loss' ? 'stop_loss_alert' : 'take_profit_alert']: !currentValue
        };
      }
      return p;
    }));

    try {
      const updateData: any = {};
      if (type === 'stop_loss') {
        updateData.stop_loss_alert = !currentValue;
      } else {
        updateData.take_profit_alert = !currentValue;
      }
      
      await axios.put(`/api/positions/${positionId}`, updateData);
      // fetchPositions(); // 不需要重新加载，因为已经乐观更新
    } catch (error) {
      // 失败回滚
      setPositions(originalPositions);
      alert('更新失败');
    }
  };

  const handleTakeProfit = async (position: Position) => {
    const result = await openPriceModal(
      'take_profit',
      position.stock_code,
      position.stock_name,
      position.current_price,
      position.take_profit_price,
      undefined,
      position.shares,
      position.shares
    );
    const nextShares = result?.shares ? parseInt(result.shares, 10) : undefined;
    const isPartial = nextShares != null && Number.isFinite(nextShares) && nextShares > 0 && nextShares < position.shares;
    if (result && result.price && !isNaN(parseFloat(result.price))) {
      const originalPositions = [...positions];
      if (isPartial && nextShares != null) {
        setPositions(prev => prev.map(p => (p.id === position.id ? { ...p, shares: p.shares - nextShares } : p)));
      } else {
        setPositions(prev => prev.filter(p => p.id !== position.id));
      }

      try {
        const requestData: any = {
          sell_price: parseFloat(result.price)
        };
        // 如果提供了日期，添加到请求中
        if (result.date) {
          requestData.close_date = result.date;
        }
        if (nextShares != null && Number.isFinite(nextShares)) {
          requestData.shares = nextShares;
        }
        await axios.post(`/api/positions/${position.id}/take-profit`, requestData);
        
        if (!isPartial) {
          clearAlertsByStockCode(position.stock_code);
        } else {
          await fetchPositions();
        }
        
        // fetchPositions(); // 不需要重新加载
        // 刷新相关面板
        refreshCalendar(); // 刷新日历标记
        refreshAnalysis(); // 刷新AI分析
        refreshUserPanel(); // 刷新用户面板（资金变化）
        refreshTradeHistory(); // 刷新开仓历史面板（显示平仓状态）
      } catch (error: any) {
        // 失败回滚
        setPositions(originalPositions);
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
      position.stop_loss_price,
      undefined,
      position.shares,
      position.shares
    );
    const nextShares = result?.shares ? parseInt(result.shares, 10) : undefined;
    const isPartial = nextShares != null && Number.isFinite(nextShares) && nextShares > 0 && nextShares < position.shares;
    if (result && result.price && !isNaN(parseFloat(result.price))) {
      const originalPositions = [...positions];
      if (isPartial && nextShares != null) {
        setPositions(prev => prev.map(p => (p.id === position.id ? { ...p, shares: p.shares - nextShares } : p)));
      } else {
        setPositions(prev => prev.filter(p => p.id !== position.id));
      }

      try {
        const requestData: any = {
          sell_price: parseFloat(result.price)
        };
        // 如果提供了日期，添加到请求中
        if (result.date) {
          requestData.close_date = result.date;
        }
        if (nextShares != null && Number.isFinite(nextShares)) {
          requestData.shares = nextShares;
        }
        await axios.post(`/api/positions/${position.id}/stop-loss`, requestData);
        
        if (!isPartial) {
          clearAlertsByStockCode(position.stock_code);
        } else {
          await fetchPositions();
        }
        
        // fetchPositions(); // 不需要重新加载
        // 刷新相关面板
        refreshCalendar(); // 刷新日历标记
        refreshAnalysis(); // 刷新AI分析
        refreshUserPanel(); // 刷新用户面板（资金变化）
        refreshTradeHistory(); // 刷新开仓历史面板（显示平仓状态）
      } catch (error: any) {
        // 失败回滚
        setPositions(originalPositions);
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

  const calculateActualSingleLoss = (position: Position) => {
    if (!position.stop_loss_price) return null;
    if (!position.buy_price || !position.shares) return null;
    return Math.abs(position.buy_price - position.stop_loss_price) * position.shares;
  };

  const lossStats = useMemo(() => {
    const losses = positions
      .map(calculateActualSingleLoss)
      .filter((v): v is number => typeof v === 'number' && Number.isFinite(v));

    const sum = losses.reduce((acc, v) => acc + v, 0);
    const max = losses.length > 0 ? Math.max(...losses) : 0;
    const avg = losses.length > 0 ? sum / losses.length : 0;

    return {
      count: losses.length,
      sum,
      max,
      avg,
    };
  }, [positions]);

  if (loading) {
    return (
      <div className="jojo-card p-6 text-center h-full flex flex-col justify-center">
        <div className="text-jojo-gold animate-jojo-pulse">加载中...</div>
      </div>
    );
  }

  return (
    <div ref={panelRef} className="jojo-card p-3 h-full flex flex-col min-h-0">
      <div className="flex justify-between items-center mb-2 flex-none">
        <h2 className="jojo-title text-lg">持仓</h2>
        <button
          onClick={() => refreshPrices(true)}
          disabled={refreshing || isSyncing}
          className="jojo-button flex items-center justify-center p-1 text-xs min-w-[50px]"
          title="手动刷新价格"
        >
          {refreshing || isSyncing ? (
            <div className="animate-spin text-jojo-gold transform-gpu">
              <RefreshCw size={16} />
            </div>
          ) : (
            <div className="flex items-center space-x-1">
              <RefreshCw size={14} />
              <span>刷新</span>
            </div>
          )}
        </button>
      </div>

      {positions.length === 0 ? (
        <div className="flex-1 min-h-0 flex items-center justify-center text-gray-400 text-sm">
          当前无持仓
        </div>
      ) : (
        <div className="flex-1 min-h-0 flex flex-col">
          <div className="mb-2 flex-none border border-jojo-gold rounded p-2 bg-jojo-blue-light text-xs text-gray-300">
            <div className="flex flex-wrap gap-x-3 gap-y-1">
              <div>
                <span className="text-gray-400">已设止损:</span> {lossStats.count}/{positions.length}
              </div>
              <div>
                <span className="text-gray-400">实际单笔损失合计:</span> ¥{lossStats.sum.toFixed(2)}
              </div>
              <div>
                <span className="text-gray-400">平均:</span> ¥{lossStats.avg.toFixed(2)}
              </div>
              <div>
                <span className="text-gray-400">最大:</span> ¥{lossStats.max.toFixed(2)}
              </div>
            </div>
          </div>

          <div className="space-y-2 flex-1 min-h-0 overflow-y-auto custom-scrollbar pr-1">
            {positions.map((position) => {
            const profit = calculateProfit(position);
            const profitPercent = profit ? ((position.current_price! - position.buy_price) / position.buy_price * 100) : null;
            const actualSingleLoss = calculateActualSingleLoss(position);
            const openedShares = position.opened_shares ?? position.shares;
            const closedShares = position.closed_shares ?? 0;
            const ratio334 = calc334Shares(openedShares);

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
                  
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-1 text-xs text-gray-300 mb-1">
                    <div>
                      <span className="text-gray-400">持仓天数:</span> {position.holding_days} 天
                    </div>
                    <div>
                      <span className="text-gray-400">剩余股数:</span> {position.shares}
                    </div>
                    <div>
                      <span className="text-gray-400">买入价:</span> ¥{position.buy_price.toFixed(2)}
                    </div>
                    <div>
                      <span className="text-gray-400">市值:</span> {position.current_price ? `¥${(position.current_price * position.shares).toFixed(2)}` : '获取中...'}
                    </div>
                    <div>
                      <span className="text-gray-400">开仓股数:</span> {openedShares}
                    </div>
                    <div>
                      <span className="text-gray-400">已平仓股数:</span> {closedShares}
                    </div>
                    <div className="xl:col-span-2">
                      <span className="text-gray-400">3:3:4参考股数:</span> {ratio334.a}/{ratio334.b}/{ratio334.c}
                    </div>
                    <div className="xl:col-span-2">
                      <span className="text-gray-400">实际单笔损失:</span>{' '}
                      {actualSingleLoss != null ? `¥${actualSingleLoss.toFixed(2)}` : '未设置止损'}
                    </div>
                  </div>
                  {position.partial_closes && position.partial_closes.length > 0 && (
                    <div className="mt-1 p-1.5 bg-jojo-blue rounded border border-jojo-gold text-xs text-gray-300">
                      <div className="flex items-center justify-between text-gray-400 mb-1">
                        <span>分段平仓记录</span>
                        <span>{position.partial_closes.length} 笔</span>
                      </div>
                      <div className="space-y-1">
                        {position.partial_closes.map((pc) => {
                          const sideLabel = pc.order_result || '平仓';
                          const priceText = typeof pc.sell_price === 'number' ? `¥${pc.sell_price.toFixed(2)}` : '';
                          const pnlText =
                            typeof pc.profit_loss === 'number'
                              ? `${pc.profit_loss >= 0 ? '+' : ''}${pc.profit_loss.toFixed(2)}`
                              : '';
                          return (
                            <div key={pc.id} className="flex items-center justify-between gap-2">
                              <div className="truncate">
                                {formatDate(pc.close_time)} {sideLabel} {pc.shares}股
                              </div>
                              <div className="shrink-0 text-right">
                                {priceText}{priceText && pnlText ? ' ' : ''}{pnlText}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

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
        </div>
      )}
      
      {/* JOJO风格弹窗 */}
      <PriceModal />
    </div>
  );
}
