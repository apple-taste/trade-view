import { useEffect, useState, useRef, useCallback } from 'react';
import axios from 'axios';
import { Plus, Edit, Trash2, Calendar, List, Trash, Loader2 } from 'lucide-react';
import { format, addDays, subDays } from 'date-fns';
import { useTrade } from '../../contexts/TradeContext';
import { useAlerts } from '../../contexts/AlertContext';
import { logger } from '../../utils/logger';
import { perfMonitor } from '../../utils/performance';
import { useJojoModal } from '../JojoModal';
import JojolandMascot from '../JojolandMascot';

// 北京时间工具函数（UTC+8）
const BEIJING_TIMEZONE_OFFSET = 8 * 60; // 8小时 = 480分钟

// 将UTC时间转换为北京时间字符串（用于datetime-local输入框）
const utcToBeijingTime = (utcDate: Date | string): string => {
  const date = typeof utcDate === 'string' ? new Date(utcDate) : utcDate;
  // 创建北京时间（UTC+8）
  // 使用UTC方法确保时区转换正确
  const utcTime = date.getTime();
  const beijingTime = new Date(utcTime + BEIJING_TIMEZONE_OFFSET * 60000);
  // 格式化为 YYYY-MM-DDTHH:mm（使用UTC方法确保格式正确）
  const year = beijingTime.getUTCFullYear();
  const month = String(beijingTime.getUTCMonth() + 1).padStart(2, '0');
  const day = String(beijingTime.getUTCDate()).padStart(2, '0');
  const hour = String(beijingTime.getUTCHours()).padStart(2, '0');
  const minute = String(beijingTime.getUTCMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hour}:${minute}`;
};

// 将北京时间字符串（来自datetime-local输入框）转换为UTC时间字符串
const beijingTimeToUTC = (beijingTimeString: string): string => {
  // datetime-local输入框返回的是本地时间格式（YYYY-MM-DDTHH:mm）
  // 我们需要将其视为北京时间（UTC+8），然后转换为UTC
  // 正确方法：直接构造UTC时间，然后减去8小时
  // 例如：2026-01-23T14:30 (北京时间) -> 2026-01-23T06:30:00Z (UTC时间)
  const [datePart, timePart] = beijingTimeString.split('T');
  const [year, month, day] = datePart.split('-').map(Number);
  const [hour, minute] = timePart.split(':').map(Number);
  
  // 直接构造UTC时间对象（使用Date.UTC创建UTC时间戳）
  // 然后减去8小时（480分钟）得到真正的UTC时间
  const utcTimestamp = Date.UTC(year, month - 1, day, hour, minute) - BEIJING_TIMEZONE_OFFSET * 60000;
  const utcDate = new Date(utcTimestamp);
  return utcDate.toISOString();
};

// 获取当前北京时间（用于默认值）
const getCurrentBeijingTime = (): string => {
  const now = new Date();
  return utcToBeijingTime(now);
};

interface Trade {
  id: number;
  stock_code: string;
  stock_name?: string;
  open_time: string;
  close_time?: string;  // 离场时间（平仓时间）
  shares: number;
  commission: number;  // 总手续费
  buy_commission?: number;  // 买入手续费
  sell_commission?: number;  // 卖出手续费
  theoretical_risk_reward_ratio?: number;  // 理论风险回报比
  actual_risk_reward_ratio?: number;  // 实际风险回报比
  buy_price: number;
  sell_price?: number;
  stop_loss_price?: number;
  take_profit_price?: number;
  stop_loss_alert: boolean;
  take_profit_alert: boolean;
  current_price?: number;
  holding_days: number;
  order_result?: string;
  notes?: string;
  status?: string;
  price_source?: string;
  risk_reward_ratio?: number; // 风险回报比
  profit_loss?: number;  // 盈亏金额（包含手续费）
}

interface TradeHistoryPanelProps {
  selectedDate: string;
}

interface StockStatistics {
  total_profit_loss: number;
  average_theoretical_risk_reward_ratio: number | null;
  trade_count: number;
}

export default function TradeHistoryPanel({ selectedDate }: TradeHistoryPanelProps) {
  const { confirm, prompt, Modal } = useJojoModal();
  // 缓存交易记录: 日期 -> 交易列表
  const tradesCache = useRef<Record<string, Trade[]>>({});
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  
  // 分页状态
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(0);
  const [totalItems, setTotalItems] = useState(0);

  const [showForm, setShowForm] = useState(false);
  const [editingTrade, setEditingTrade] = useState<Trade | null>(null);
  const [viewMode, setViewMode] = useState<'date' | 'all'>('date');
  const [stockCodes, setStockCodes] = useState<Array<{code: string; name: string}>>([]);
  const [selectedStockCode, setSelectedStockCode] = useState<string | null>(null);
  const [selectedStockName, setSelectedStockName] = useState<string | null>(null);
  const [stockStatistics, setStockStatistics] = useState<StockStatistics | null>(null);
  const { 
    refreshCalendar, 
    refreshPositions, 
    refreshAnalysis, 
    refreshUserPanel, 
    _tradeHistoryRefreshKey, 
    setLastAddedTrade,
    setLastUpdatedTrade,
    setLastDeletedTradeId,
    strategies,
    effectiveStrategyId,
    setCurrentStrategyId,
    createStrategy,
    deleteStrategy,
    deleteAllStrategies
  } = useTrade();
  const { clearAlertsByStockCode } = useAlerts();

  const handleClearAllStrategies = async () => {
    if (strategies.length === 0) return;
    const firstConfirm = await confirm(
      '⚠️ 清空所有策略',
      `确定要删除所有策略吗？\n\n此操作将：\n• 删除所有策略\n• 清空所有交易记录\n• 清空资金曲线\n\n此操作不可恢复！`
    );
    if (!firstConfirm) return;
    const secondConfirm = await confirm(
      '⚠️ 最终确认',
      `请再次确认：您真的要清空所有策略吗？`
    );
    if (!secondConfirm) return;
    try {
      await deleteAllStrategies();
      alert('✅ 已清空所有策略');
    } catch (error: any) {
      console.error('清空策略失败:', error);
      alert('❌ 操作失败');
    }
  };

  const getCacheKey = useCallback(
    (dateStr: string) => `${effectiveStrategyId ?? 'default'}_${dateStr}`,
    [effectiveStrategyId]
  );

  // 将选中日期转换为北京时间格式（用于datetime-local输入框）
  const getSelectedDateBeijingTime = (): string => {
    if (selectedDate) {
      // selectedDate是YYYY-MM-DD格式，需要转换为YYYY-MM-DDTHH:mm格式
      // 默认使用当前时间的时分，但日期使用selectedDate
      const now = new Date();
      const beijingNow = utcToBeijingTime(now);
      // 提取时分部分
      const timePart = beijingNow.split('T')[1];
      // 组合为选中日期的北京时间
      return `${selectedDate}T${timePart}`;
    }
    return getCurrentBeijingTime();
  };

  const [formData, setFormData] = useState({
    stock_code: '',
    stock_name: '',
    open_time: getSelectedDateBeijingTime(), // 使用选中日期的北京时间
    close_time: '',  // 离场时间（用于编辑已平仓交易）
    shares: '',
    risk_per_trade: '',  // 单笔风险（用于自动计算手数）
    commission: '0',
    buy_commission: '',  // 买入手续费，留空自动计算
    sell_commission: '',  // 卖出手续费，留空自动计算
    buy_price: '',
    sell_price: '',  // 离场价格（用于编辑已平仓交易）
    stop_loss_price: '',
    take_profit_price: '',
    stop_loss_alert: false,
    take_profit_alert: false,
    notes: ''
  });
  
  // 跟踪用户是否手动修改了手数（如果手动修改，不再自动计算）
  const [sharesManuallySet, setSharesManuallySet] = useState(false);
  
  // 自动计算手数：当单笔风险、买入价格和止损价格都填写时
  useEffect(() => {
    if (!sharesManuallySet && formData.risk_per_trade && formData.buy_price && formData.stop_loss_price) {
      const riskPerTrade = parseFloat(formData.risk_per_trade);
      const buyPrice = parseFloat(formData.buy_price);
      const stopLossPrice = parseFloat(formData.stop_loss_price);
      
      if (!isNaN(riskPerTrade) && !isNaN(buyPrice) && !isNaN(stopLossPrice) && 
          riskPerTrade > 0 && buyPrice > stopLossPrice) {
        // 计算每股风险
        const riskPerShare = buyPrice - stopLossPrice;
        // 计算手数：单笔风险 / 每股风险，向上取整
        const calculatedShares = Math.ceil(riskPerTrade / riskPerShare);
        
        if (calculatedShares > 0) {
          setFormData(prev => ({ ...prev, shares: calculatedShares.toString() }));
          logger.info(`💰 [单笔风险] 自动计算手数: ${calculatedShares} (单笔风险: ${riskPerTrade}, 每股风险: ${riskPerShare.toFixed(2)})`);
        }
      }
    }
  }, [formData.risk_per_trade, formData.buy_price, formData.stop_loss_price, sharesManuallySet]);

  const fetchTrades = useCallback(async (forceRefresh = false) => {
    const cacheKey = getCacheKey(selectedDate);
    // 如果是日期视图且有缓存，优先使用缓存
    if (viewMode === 'date' && !forceRefresh && tradesCache.current[cacheKey]) {
      const cachedData = tradesCache.current[cacheKey];
      setTrades(cachedData);
      setStockStatistics(null);
      return;
    }

    setLoading(true);
    if (effectiveStrategyId == null) {
      setTrades([]);
      setTotalPages(0);
      setTotalItems(0);
      setStockStatistics(null);
      setLoading(false);
      return;
    }
    // 性能监控开始
    const perfLabel = viewMode === 'all' ? `TradeHistory_FetchAll_Page${page}` : `TradeHistory_FetchDate_${selectedDate}`;
    perfMonitor.start(perfLabel);
    
    try {
      if (viewMode === 'all') {
        const response = await axios.get('/api/trades', {
          params: { page, page_size: pageSize, strategy_id: effectiveStrategyId }
        });
        
        // 处理分页响应
        if (response.data.items) {
          setTrades(response.data.items);
          setTotalPages(response.data.total_pages);
          setTotalItems(response.data.total);
        } else if (Array.isArray(response.data)) {
          // 兼容旧格式（虽然后端已经改了，但保留以防万一）
          setTrades(response.data);
          setTotalPages(1);
          setTotalItems(response.data.length);
        }
        
        setStockStatistics(null);
      } else {
        const response = await axios.get(`/api/trades/date/${selectedDate}`, {
          params: { strategy_id: effectiveStrategyId },
        });
        const data = response.data;
        // 更新缓存
        tradesCache.current[cacheKey] = data;
        setTrades(data);
        setStockStatistics(null);
      }
    } catch (error) {
      console.error('获取交易记录失败:', error);
    } finally {
      perfMonitor.end(perfLabel);
      setLoading(false);
    }
  }, [effectiveStrategyId, getCacheKey, page, pageSize, selectedDate, viewMode]);

  // 监听外部刷新信号，清除缓存并刷新
  useEffect(() => {
    if (_tradeHistoryRefreshKey > 0) {
      if (selectedDate) {
        const key = getCacheKey(selectedDate);
        if (tradesCache.current[key]) {
          delete tradesCache.current[key];
        }
      }
      fetchTrades(true);
    }
  }, [_tradeHistoryRefreshKey, fetchTrades, getCacheKey, selectedDate]);

  const fetchStockCodes = async () => {
    try {
      if (effectiveStrategyId == null) {
        setStockCodes([]);
        return;
      }
      const response = await axios.get('/api/trades/stock-codes', {
        params: { strategy_id: effectiveStrategyId },
      });
      setStockCodes(response.data);
    } catch (error) {
      console.error('获取股票代码列表失败:', error);
    }
  };

  const fetchTradesByStockCode = async (stockCode: string) => {
    setLoading(true);
    try {
      if (effectiveStrategyId == null) {
        setTrades([]);
        setStockStatistics(null);
        setSelectedStockName(null);
        return;
      }
      const response = await axios.get(`/api/trades/stock/${stockCode}`, {
        params: { strategy_id: effectiveStrategyId },
      });
      setTrades(response.data.trades);
      setStockStatistics(response.data.statistics);
      // 从交易记录中获取股票名称（取第一条记录的股票名称）
      if (response.data.trades && response.data.trades.length > 0) {
        const firstTrade = response.data.trades[0];
        setSelectedStockName(firstTrade.stock_name || null);
      }
    } catch (error) {
      console.error('获取股票交易记录失败:', error);
      setTrades([]);
      setStockStatistics(null);
      setSelectedStockName(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 当fetchTrades依赖变化时（包括分页、视图模式、日期），重新获取数据
    fetchTrades();
  }, [fetchTrades]);

  useEffect(() => {
    // 视图模式改变时的副作用
    if (viewMode === 'all') {
      fetchStockCodes();
    } else {
      setSelectedStockCode(null);
      setSelectedStockName(null);
      setStockStatistics(null);
    }
  }, [viewMode]);

  useEffect(() => {
    tradesCache.current = {};
    setSelectedStockCode(null);
    setSelectedStockName(null);
    setStockStatistics(null);
    if (viewMode === 'all') {
      fetchStockCodes();
    } else {
      fetchTrades(true);
    }
  }, [effectiveStrategyId]);

  const handleCreateStrategy = async () => {
    const name = await prompt('⭐ 新建策略', '请输入策略名称', '', '例如：短线低吸');
    if (!name) return;
    await createStrategy(name);
  };

  const handleDeleteCurrentStrategy = async () => {
    const current = effectiveStrategyId != null ? strategies.find((s) => s.id === effectiveStrategyId) : null;
    if (!current) return;
    const ok = await confirm('🗑️ 删除策略', `确定删除策略「${current.name}」吗？\n\n该策略下交易将被清空（软删除），资金曲线记录也会删除。`);
    if (!ok) return;
    await deleteStrategy(current.id);
  };

  useEffect(() => {
    if (viewMode === 'all' && selectedStockCode) {
      fetchTradesByStockCode(selectedStockCode);
    } else if (viewMode === 'all' && !selectedStockCode) {
      fetchTrades();
    }
  }, [selectedStockCode, viewMode]);

  // 预加载相邻日期的交易记录
  useEffect(() => {
    // 预加载相邻日期的交易记录
    if (viewMode === 'date') {
      const preloadDate = async (dateStr: string) => {
        if (effectiveStrategyId == null) return;
        const key = getCacheKey(dateStr);
        if (!tradesCache.current[key]) {
          try {
            const response = await axios.get(`/api/trades/date/${dateStr}`, {
              params: { strategy_id: effectiveStrategyId },
            });
            tradesCache.current[key] = response.data;
            // logger.info(`✅ [TradeHistory] 预加载成功: ${dateStr}`);
          } catch (err) {
            // 忽略预加载错误
          }
        }
      };

      const currentDate = new Date(selectedDate);
      // 简单的防抖：延迟预加载，优先保证当前页面渲染
      const timer = setTimeout(() => {
        const prevDate = format(subDays(currentDate, 1), 'yyyy-MM-dd');
        const nextDate = format(addDays(currentDate, 1), 'yyyy-MM-dd');
        preloadDate(prevDate);
        preloadDate(nextDate);
      }, 300);

      return () => clearTimeout(timer);
    }
  }, [effectiveStrategyId, getCacheKey, selectedDate, viewMode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (effectiveStrategyId == null) {
        alert('请先创建并选择策略');
        return;
      }
      // 将北京时间转换为UTC时间发送给后端
      const utcTimeString = beijingTimeToUTC(formData.open_time);
      
      // 处理离场时间（如果提供了）
      let utcCloseTimeString = undefined;
      if (formData.close_time) {
        utcCloseTimeString = beijingTimeToUTC(formData.close_time);
      }
      
      const data: any = {
        stock_code: formData.stock_code,
        stock_name: formData.stock_name || undefined,
        shares: formData.shares ? parseInt(formData.shares) : undefined,
        commission: parseFloat(formData.commission),
        buy_commission: formData.buy_commission ? parseFloat(formData.buy_commission) : undefined,
        sell_commission: formData.sell_commission ? parseFloat(formData.sell_commission) : undefined,
        buy_price: parseFloat(formData.buy_price),
        sell_price: formData.sell_price ? parseFloat(formData.sell_price) : undefined,
        stop_loss_price: formData.stop_loss_price ? parseFloat(formData.stop_loss_price) : undefined,
        take_profit_price: formData.take_profit_price ? parseFloat(formData.take_profit_price) : undefined,
        stop_loss_alert: formData.stop_loss_alert,
        take_profit_alert: formData.take_profit_alert,
        notes: formData.notes || undefined,
        open_time: utcTimeString,
        close_time: utcCloseTimeString || undefined  // 明确设置为 undefined 如果为空
      };
      data.strategy_id = effectiveStrategyId;
      
      let response;
      // 编辑时不需要发送 risk_per_trade
      if (editingTrade) {
        // 移除不需要的字段
        delete data.risk_per_trade;
        
        console.log('📝 [编辑交易] 发送更新数据:', data);
        response = await axios.put(`/api/trades/${editingTrade.id}`, data);
      } else {
        // 新建交易时，如果用户提供了手数，优先使用手数；否则使用单笔风险
        if (!data.shares && formData.risk_per_trade) {
          data.risk_per_trade = parseFloat(formData.risk_per_trade);
          delete data.shares;
        } else if (data.shares) {
          delete data.risk_per_trade;
        }
        
        console.log('📝 [新建交易] 发送创建数据:', data);
        response = await axios.post('/api/trades', data);
      }

      // 乐观UI更新：先关闭弹窗，再后台刷新
      setShowForm(false);
      setEditingTrade(null);
      resetForm();

      // 手动更新本地列表，减少视觉等待
      if (editingTrade) {
        setTrades(prev => prev.map(t => t.id === response.data.id ? response.data : t));
        setLastUpdatedTrade(response.data);
      } else {
        setTrades(prev => [response.data, ...prev]);
        setLastAddedTrade(response.data);
      }
      
      // 清除当前日期缓存，确保获取最新数据
      tradesCache.current = {};

      // 后台异步刷新相关面板，不阻塞UI交互
      setTimeout(() => {
        Promise.all([
          fetchTrades(true), // 刷新当前列表以确保一致性
          refreshCalendar(), // 刷新日历标记
          // refreshPositions(), // 刷新持仓 (通过增量更新机制处理，避免全量刷新)
          refreshAnalysis(), // 刷新AI分析
          refreshUserPanel() // 刷新用户面板
        ]).catch(err => {
          console.error('后台刷新失败:', err);
        });
      }, 10);
      
      logger.info(`✅ [TradeHistory] 交易保存成功，已触发后台刷新`);
    } catch (error: any) {
      console.error('❌ [交易操作] 操作失败:', error);
      // 如果失败，确保表单保持打开状态
      setShowForm(true);
      const errorMessage = error.response?.data?.detail || error.message || '操作失败';
      alert(`❌ 操作失败\n\n${errorMessage}`);
    }
  };

  const handleEdit = (trade: Trade) => {
    setEditingTrade(trade);
    // 将UTC时间转换为北京时间显示（datetime-local输入框需要北京时间格式）
    const beijingTimeString = utcToBeijingTime(trade.open_time);
    const beijingCloseTimeString = trade.close_time ? utcToBeijingTime(trade.close_time) : '';
    
    setFormData({
      stock_code: trade.stock_code,
      stock_name: trade.stock_name || '',
      open_time: beijingTimeString,
      close_time: beijingCloseTimeString,  // 离场时间
      shares: trade.shares.toString(),
      risk_per_trade: '',  // 编辑时不使用单笔风险
      commission: trade.commission.toString(),
      buy_commission: trade.buy_commission?.toString() || '',  // 买入手续费
      sell_commission: trade.sell_commission?.toString() || '',  // 卖出手续费
      buy_price: trade.buy_price.toString(),
      sell_price: trade.sell_price?.toString() || '',  // 离场价格
      stop_loss_price: trade.stop_loss_price?.toString() || '',
      take_profit_price: trade.take_profit_price?.toString() || '',
      stop_loss_alert: trade.stop_loss_alert,
      take_profit_alert: trade.take_profit_alert,
      notes: trade.notes || ''
    });
    setSharesManuallySet(true);  // 编辑时手数已设置，不自动计算
    setShowForm(true);
  };

  const handleClearAll = async () => {
    const confirmMessage = `⚠️ 警告：确定要清空所有历史交易记录吗？

此操作将：
• 删除所有交易记录（软删除）
• 重新计算资金曲线（恢复到初始资金）
• 清除所有持仓记录

此操作不可恢复！`;
    
    const firstConfirm = await confirm('⚠️ 清空所有交易记录', confirmMessage);
    if (!firstConfirm) return;
    
    // 二次确认
    const secondConfirmMessage = `⚠️ 最后确认：您真的要清空所有历史交易记录吗？

清空后，总资产将恢复到初始资金状态。

点击确定继续，或点击取消放弃。`;
    const secondConfirm = await confirm('⚠️ 最终确认', secondConfirmMessage);
    if (!secondConfirm) return;
    
    try {
      logger.info('🗑️ [TradeHistory] 清空所有交易记录（后端一次性处理）...');
      const res = await axios.delete('/api/trades/clear-all', {
        params: { strategy_id: effectiveStrategyId ?? undefined },
      });

      // 等待后端重算落库
      await new Promise(resolve => setTimeout(resolve, 400));

      alert(`✅ 已清空交易记录\n\n删除数量：${res.data?.deleted_count ?? 0}\n💡 总资产已恢复到初始资金状态`);

      tradesCache.current = {};

      // 刷新相关面板
      refreshCalendar();
      refreshPositions();
      refreshAnalysis();
      refreshUserPanel();
      fetchTrades();
    } catch (error: any) {
      logger.error('❌ [TradeHistory] 清空失败', error.response?.data || error.message);
      alert(error.response?.data?.detail || '清空失败，请稍后重试');
    }
  };

  const handleDelete = async (id: number) => {
    // 找到要删除的交易记录
    const tradeToDelete = trades.find(t => t.id === id);
    if (!tradeToDelete) return;
    
    const hasAlerts = (tradeToDelete.stop_loss_alert && tradeToDelete.stop_loss_price) ||
                      (tradeToDelete.take_profit_alert && tradeToDelete.take_profit_price);
    
    const confirmMessage = hasAlerts 
      ? `确定要删除这条交易记录吗？

⚠️ 注意：该交易已设置止损/止盈提醒，删除后将自动取消提醒。

💡 删除后，资金曲线将重新计算（排除此交易）。`
      : `确定要删除这条交易记录吗？

💡 删除后，资金曲线将重新计算（排除此交易）。`;
    
    const userConfirm = await confirm(`🗑️ 删除交易 ${tradeToDelete.stock_code}`, confirmMessage);
    if (!userConfirm) return;

    try {
      logger.info(`🗑️ [TradeHistory] 删除交易记录 ID: ${id}`);
      await axios.delete(`/api/trades/${id}`);
      
      // 乐观UI更新：立即从列表中移除
      setTrades(prev => prev.filter(t => t.id !== id));
      setLastDeletedTradeId(id);
      
      // 清除与该交易相关的所有提醒（止损和止盈）
      if (hasAlerts) {
        clearAlertsByStockCode(tradeToDelete.stock_code);
      }
      
      // 清除缓存
      if (selectedDate) {
        const key = getCacheKey(selectedDate);
        if (tradesCache.current[key]) {
          delete tradesCache.current[key];
        }
      }

      logger.info(`✅ [TradeHistory] 交易记录已删除，后台正在刷新数据...`);

      // 后台异步刷新相关面板
      setTimeout(() => {
        Promise.all([
          fetchTrades(true), // 确保数据一致性
          refreshCalendar(), // 刷新日历标记
          // refreshPositions(), // 刷新持仓
          refreshAnalysis(), // 刷新AI分析
          refreshUserPanel() // 刷新用户面板（重新获取资金数据）
        ]).catch(err => {
          console.error('后台刷新失败:', err);
        });
      }, 500); // 保持短暂延迟以确保后端计算完成
      
    } catch (error: any) {
      logger.error('❌ [TradeHistory] 删除失败', error.response?.data || error.message);
      alert('删除失败');
    }
  };

  const resetForm = () => {
    setFormData({
      stock_code: '',
      stock_name: '',
      open_time: getSelectedDateBeijingTime(), // 使用选中日期的北京时间
      close_time: '',  // 离场时间
      shares: '',
      risk_per_trade: '',  // 单笔风险
      commission: '0',
      buy_commission: '',  // 买入手续费，留空自动计算
      sell_commission: '',  // 卖出手续费，留空自动计算
      buy_price: '',
      sell_price: '',  // 离场价格
      stop_loss_price: '',
      take_profit_price: '',
      stop_loss_alert: false,
      take_profit_alert: false,
      notes: ''
    });
    setSharesManuallySet(false);
  };

  const parseStockCode = (input: string) => {
    const parts = input.split('-');
    return {
      code: parts[0].trim(),
      name: parts[1]?.trim() || ''
    };
  };

  if (loading) {
    return (
      <div className="jojo-card p-3 h-full flex flex-col items-center justify-center text-center">
        <div className="text-jojo-gold animate-jojo-pulse text-sm">加载中...</div>
      </div>
    );
  }

  return (
    <div className="jojo-card p-3 h-full flex flex-col min-h-0">
      <div className="flex items-center mb-2 gap-2 min-w-0">
        <div className="flex items-center space-x-2 min-w-0">
          <h2 className="jojo-title text-lg whitespace-nowrap">开仓记录历史</h2>
          <div className="flex items-center gap-1 min-w-0 flex-wrap">
            <select
              value={effectiveStrategyId ?? ''}
              onChange={(e) => setCurrentStrategyId(e.target.value ? Number(e.target.value) : null)}
              className="jojo-input text-xs py-1 w-[140px] md:w-[180px]"
            >
              <option value="">请选择策略</option>
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
            <button onClick={handleCreateStrategy} className="jojo-button text-xs px-2 py-1" title="新建策略">
              新建
            </button>
            <button
              onClick={handleDeleteCurrentStrategy}
              className="jojo-button-danger text-xs px-2 py-1"
              title="删除当前策略"
              disabled={!effectiveStrategyId}
            >
              删除
            </button>
            {strategies.length > 0 && (
              <button
                onClick={handleClearAllStrategies}
                className="jojo-button-danger text-xs px-2 py-1 ml-1 bg-red-800/50 border-red-800 hover:bg-red-800"
                title="清空所有策略"
              >
                清空策略
              </button>
            )}
          </div>
          <div className="flex items-center space-x-1 bg-jojo-blue-light rounded p-0.5 border border-jojo-gold">
            <button
              onClick={() => setViewMode('date')}
              className={`px-2 py-0.5 rounded text-xs flex items-center space-x-1 transition-all ${
                viewMode === 'date'
                  ? 'bg-jojo-gold text-jojo-blue font-bold'
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              <Calendar size={12} />
              <span>按日期</span>
            </button>
            <button
              onClick={() => setViewMode('all')}
              className={`px-2 py-0.5 rounded text-xs flex items-center space-x-1 transition-all ${
                viewMode === 'all'
                  ? 'bg-jojo-gold text-jojo-blue font-bold'
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              <List size={12} />
              <span>全部历史</span>
            </button>
          </div>
        </div>
        <div className="flex-1 flex justify-center px-2 min-w-0">
          <JojolandMascot inline />
        </div>
        <div className="flex items-center space-x-1 flex-shrink-0">
          <button
            onClick={() => {
              resetForm();
              setEditingTrade(null);
              setShowForm(true);
            }}
            className="jojo-button flex items-center space-x-1 text-xs px-2 py-1"
          >
            <Plus size={14} />
            <span>添加</span>
          </button>
          {viewMode === 'all' && trades.length > 0 && (
            <button
              onClick={handleClearAll}
              className="jojo-button-danger flex items-center space-x-1 text-xs px-2 py-1"
              title="清空所有历史交易记录"
            >
              <Trash size={14} />
              <span>清空</span>
            </button>
          )}
        </div>
      </div>

      {/* 显示当前查看模式 */}
      {viewMode === 'date' && (
        <div className="mb-2 p-1 bg-jojo-blue-light rounded text-xs text-gray-300">
          查看日期: {new Date(selectedDate).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })}
        </div>
      )}
      {viewMode === 'all' && (
        <div className="mb-2 space-y-2">
          <div className="p-1 bg-jojo-blue-light rounded text-xs text-jojo-gold">
            📋 查看全部历史订单 {selectedStockCode ? (
              <span className="text-white">
                - {selectedStockCode} {selectedStockName && `(${selectedStockName})`}
              </span>
            ) : ''} ({trades.length} 条记录)
          </div>
          
          {/* 股票代码筛选器 */}
          {stockCodes.length > 0 && (
            <div className="p-2 bg-jojo-blue-light rounded border border-jojo-gold">
              <div className="text-xs text-jojo-gold mb-2 font-semibold">📊 按股票代码筛选：</div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => {
                    setSelectedStockCode(null);
                    setSelectedStockName(null);
                    setStockStatistics(null);
                  }}
                  className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                    selectedStockCode === null
                      ? 'bg-jojo-gold text-gray-900 shadow-lg'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  全部 ({stockCodes.length})
                </button>
                {stockCodes.map((stock) => (
                  <button
                    key={stock.code}
                    onClick={() => setSelectedStockCode(stock.code)}
                    className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                      selectedStockCode === stock.code
                        ? 'bg-jojo-gold text-gray-900 shadow-lg'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                    title={stock.name || stock.code}
                  >
                    {stock.code} {stock.name && <span className="text-gray-400">({stock.name})</span>}
                  </button>
                ))}
              </div>
            </div>
          )}
          
          {/* 选中股票的统计信息 */}
          {selectedStockCode && stockStatistics && (
            <div className="p-3 bg-gradient-to-r from-jojo-blue-light to-jojo-blue-dark rounded border-2 border-jojo-gold">
              <div className="text-sm font-bold text-jojo-gold mb-2">
                📈 {selectedStockCode} {selectedStockName && <span className="text-white">({selectedStockName})</span>} 交易统计
              </div>
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="bg-gray-800/50 p-2 rounded">
                  <div className="text-gray-400 mb-1">交易次数</div>
                  <div className="text-lg font-bold text-white">{stockStatistics.trade_count}</div>
                </div>
                <div className={`bg-gray-800/50 p-2 rounded ${
                  stockStatistics.total_profit_loss >= 0 ? 'border-2 border-green-500' : 'border-2 border-red-500'
                }`}>
                  <div className="text-gray-400 mb-1">合计盈亏</div>
                  <div className={`text-lg font-bold ${
                    stockStatistics.total_profit_loss >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {stockStatistics.total_profit_loss >= 0 ? '+' : ''}
                    {stockStatistics.total_profit_loss.toFixed(2)} 元
                  </div>
                </div>
                <div className="bg-gray-800/50 p-2 rounded">
                  <div className="text-gray-400 mb-1">平均理论风险回报比</div>
                  <div className="text-lg font-bold text-white">
                    {stockStatistics.average_theoretical_risk_reward_ratio !== null
                      ? stockStatistics.average_theoretical_risk_reward_ratio.toFixed(2)
                      : 'N/A'}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-2 p-2 bg-jojo-blue-light rounded space-y-2 border border-jojo-gold text-xs overflow-x-hidden max-w-full">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
            {/* 提示信息 */}
            {formData.risk_per_trade && formData.buy_price && formData.stop_loss_price && !sharesManuallySet && (
              <div className="col-span-2 p-2 bg-green-500/20 border border-green-500/50 rounded text-xs text-green-300">
                💡 <strong>自动计算手数模式</strong>：已根据单笔风险 {formData.risk_per_trade} 元自动计算手数为 {formData.shares || '计算中...'} 股
                <br />
                <span className="text-gray-400">如需手动设置手数，请直接在手数字段输入，系统将停止自动计算</span>
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-jojo-gold mb-1">
                股票代码（格式：600879-航空电子）
              </label>
              <input
                type="text"
                value={formData.stock_code}
                onChange={(e) => {
                  const parsed = parseStockCode(e.target.value);
                  setFormData({
                    ...formData,
                    stock_code: parsed.code,
                    stock_name: parsed.name
                  });
                }}
                className="jojo-input"
                required
              />
            </div>
            <div className="w-full">
              <label className="block text-sm font-medium text-jojo-gold mb-1">开仓时间</label>
              <input
                type="datetime-local"
                value={formData.open_time}
                onChange={(e) => setFormData({ ...formData, open_time: e.target.value })}
                className="jojo-input w-full max-w-full"
                style={{ maxWidth: '100%', boxSizing: 'border-box' }}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-jojo-gold mb-1">
                手数
                {formData.risk_per_trade && formData.buy_price && formData.stop_loss_price && (
                  <span className="text-xs text-green-400 ml-1">(自动计算)</span>
                )}
              </label>
              <input
                type="number"
                value={formData.shares}
                onChange={(e) => {
                  setFormData({ ...formData, shares: e.target.value });
                  setSharesManuallySet(true);  // 标记为手动设置
                }}
                className="jojo-input"
                placeholder={formData.risk_per_trade ? "自动计算" : "必填"}
                required={!formData.risk_per_trade}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-jojo-gold mb-1">
                单笔风险（元）
                <span className="text-xs text-gray-400 ml-1">可选，用于自动计算手数</span>
              </label>
              <input
                type="number"
                step="0.01"
                value={formData.risk_per_trade}
                onChange={(e) => {
                  setFormData({ ...formData, risk_per_trade: e.target.value });
                  setSharesManuallySet(false);  // 重置手动设置标志，允许自动计算
                }}
                className="jojo-input"
                placeholder="例如：500（表示单笔最多亏损500元）"
              />
              {formData.risk_per_trade && formData.buy_price && formData.stop_loss_price && (
                <div className="text-xs text-green-400 mt-1">
                  💡 手数 = {formData.risk_per_trade} / ({formData.buy_price} - {formData.stop_loss_price}) = {formData.shares || '计算中...'}
                </div>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-jojo-gold mb-1">入场价格</label>
              <input
                type="number"
                step="0.01"
                value={formData.buy_price}
                onChange={(e) => {
                  setFormData({ ...formData, buy_price: e.target.value });
                  setSharesManuallySet(false);  // 重置手动设置标志，允许自动计算
                }}
                className="jojo-input"
                required
              />
            </div>
            {/* 编辑已平仓交易时显示离场价格和离场时间 - 只要有sell_price或close_time就显示 */}
            {editingTrade && (editingTrade.sell_price || editingTrade.close_time || formData.sell_price || formData.close_time) && (
              <>
                <div className="col-span-1 md:col-span-2">
                  <div className="p-2 bg-blue-500/20 border border-blue-500/50 rounded text-xs text-blue-300 mb-2">
                    💡 <strong>编辑已平仓交易</strong>：可以修改离场价格和离场时间，修改后会自动重新计算盈亏和资金曲线
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-jojo-gold mb-1">
                    离场价格
                    <span className="text-xs text-gray-400 ml-1">(修改后会自动重新计算盈亏和资金)</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.sell_price}
                    onChange={(e) => setFormData({ ...formData, sell_price: e.target.value })}
                    className="jojo-input w-full"
                    placeholder="例如：15.50"
                  />
                </div>
                <div className="w-full">
                  <label className="block text-sm font-medium text-jojo-gold mb-1">离场时间</label>
                  <input
                    type="datetime-local"
                    value={formData.close_time}
                    onChange={(e) => setFormData({ ...formData, close_time: e.target.value })}
                    className="jojo-input w-full max-w-full"
                    style={{ maxWidth: '100%', boxSizing: 'border-box' }}
                  />
                </div>
              </>
            )}
            <div>
              <label className="block text-sm font-medium text-jojo-gold mb-1">止损价格</label>
              <input
                type="number"
                step="0.01"
                value={formData.stop_loss_price}
                onChange={(e) => {
                  setFormData({ ...formData, stop_loss_price: e.target.value });
                  setSharesManuallySet(false);  // 重置手动设置标志，允许自动计算
                }}
                className="jojo-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-jojo-gold mb-1">止盈价格</label>
              <input
                type="number"
                step="0.01"
                value={formData.take_profit_price}
                onChange={(e) => setFormData({ ...formData, take_profit_price: e.target.value })}
                className="jojo-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-jojo-gold mb-1">买入手续费</label>
              <input
                type="number"
                step="0.01"
                value={formData.buy_commission || ''}
                onChange={(e) => setFormData({ ...formData, buy_commission: e.target.value })}
                className="jojo-input"
                placeholder="留空自动计算"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-jojo-gold mb-1">卖出手续费</label>
              <input
                type="number"
                step="0.01"
                value={formData.sell_commission || ''}
                onChange={(e) => setFormData({ ...formData, sell_commission: e.target.value })}
                className="jojo-input"
                placeholder="留空自动计算"
              />
            </div>
            <div className="space-y-2">
              <label className="flex items-center space-x-2 text-jojo-gold">
                <input
                  type="checkbox"
                  checked={formData.stop_loss_alert}
                  onChange={(e) => setFormData({ ...formData, stop_loss_alert: e.target.checked })}
                  className="w-4 h-4"
                />
                <span className="text-sm">止损价格闹铃</span>
              </label>
              <label className="flex items-center space-x-2 text-jojo-gold">
                <input
                  type="checkbox"
                  checked={formData.take_profit_alert}
                  onChange={(e) => setFormData({ ...formData, take_profit_alert: e.target.checked })}
                  className="w-4 h-4"
                />
                <span className="text-sm">止盈价格闹铃</span>
              </label>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-jojo-gold mb-1">交易备注</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="jojo-input"
              rows={3}
            />
          </div>
          <div className="flex space-x-2">
            <button
              type="submit"
              className="jojo-button"
            >
              {editingTrade ? '更新' : '创建'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowForm(false);
                setEditingTrade(null);
                resetForm();
              }}
              className="jojo-button-danger"
            >
              取消
            </button>
          </div>
        </form>
      )}

      <div className="overflow-x-auto flex-1 overflow-y-auto custom-scrollbar min-h-0">
        <table className="jojo-table text-xs">
          <thead className="sticky top-0 bg-jojo-blue">
            <tr>
              <th className="py-1 px-2">代码/名称</th>
              {viewMode === 'all' && <th className="py-1 px-2">开仓时间</th>}
              {viewMode === 'all' && <th className="py-1 px-2">离场时间</th>}
              <th className="py-1 px-2">手数</th>
              <th className="py-1 px-2">入场价格</th>
              {viewMode === 'all' && <th className="py-1 px-2">离场价格</th>}
              <th className="py-1 px-2">止损价格</th>
              <th className="py-1 px-2">止盈价格</th>
              <th className="py-1 px-2">理论风险比</th>
              {viewMode === 'all' && <th className="py-1 px-2">实际风险比</th>}
              <th className="py-1 px-2">买入手续费</th>
              {viewMode === 'all' && <th className="py-1 px-2">卖出手续费</th>}
              <th className="py-1 px-2">总手续费</th>
              {viewMode === 'all' && <th className="py-1 px-2">订单结果</th>}
              {viewMode === 'all' && <th className="py-1 px-2">盈亏</th>}
              <th className="py-1 px-2">出场闹铃</th>
              <th className="py-1 px-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={viewMode === 'all' ? 17 : 11} className="px-2 py-8 text-center text-gray-400">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <Loader2 className="animate-spin text-jojo-gold" size={24} />
                    <span>加载交易记录中...</span>
                  </div>
                </td>
              </tr>
            ) : trades.length === 0 ? (
              <tr>
                <td colSpan={viewMode === 'all' ? 17 : 11} className="px-2 py-4 text-center text-gray-400">
                  {viewMode === 'all' ? '暂无交易记录' : '该日期暂无交易记录'}
                </td>
              </tr>
            ) : (
              trades.map((trade) => (
                <tr key={trade.id} className="hover:bg-jojo-blue-light">
                  <td className="py-1 px-2">
                    <div className="font-bold text-jojo-gold text-xs">
                      <div>{trade.stock_code}</div>
                      <div className="text-white text-xs font-normal mt-0.5">
                        {trade.stock_name || <span className="text-gray-500 italic">(未设置名称)</span>}
                      </div>
                    </div>
                  </td>
                  {viewMode === 'all' && (
                    <td className="py-1 px-2 text-xs">
                      {new Date(trade.open_time).toLocaleString('zh-CN', {
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </td>
                  )}
                  {viewMode === 'all' && (
                    <td className="py-1 px-2 text-xs">
                      {trade.close_time ? (
                        new Date(trade.close_time).toLocaleString('zh-CN', {
                          year: 'numeric',
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit'
                        })
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </td>
                  )}
                  <td className="py-1 px-2">{trade.shares}</td>
                  <td className="py-1 px-2">¥{trade.buy_price.toFixed(2)}</td>
                  {viewMode === 'all' && (
                    <td className="py-1 px-2">
                      {trade.sell_price ? (
                        <span className={`font-semibold ${
                          trade.sell_price > trade.buy_price ? 'text-green-400' :
                          trade.sell_price < trade.buy_price ? 'text-red-400' :
                          'text-gray-300'
                        }`}>
                          ¥{trade.sell_price.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </td>
                  )}
                  <td className="py-1 px-2">{trade.stop_loss_price ? `¥${trade.stop_loss_price.toFixed(2)}` : '-'}</td>
                  <td className="py-1 px-2">{trade.take_profit_price ? `¥${trade.take_profit_price.toFixed(2)}` : '-'}</td>
                  <td className="py-1 px-2">
                    {trade.theoretical_risk_reward_ratio !== null && trade.theoretical_risk_reward_ratio !== undefined && !isNaN(trade.theoretical_risk_reward_ratio) ? (
                      <span className={`font-semibold ${
                        trade.theoretical_risk_reward_ratio >= 2 ? 'text-green-400' :
                        trade.theoretical_risk_reward_ratio >= 1 ? 'text-yellow-400' :
                        'text-red-400'
                      }`}>
                        {trade.theoretical_risk_reward_ratio.toFixed(2)}:1
                      </span>
                    ) : (
                      <span className="text-gray-500">-</span>
                    )}
                  </td>
                  {viewMode === 'all' && (
                    <td className="py-1 px-2">
                      {trade.actual_risk_reward_ratio !== null && trade.actual_risk_reward_ratio !== undefined && !isNaN(trade.actual_risk_reward_ratio) ? (
                        <span className={`font-semibold ${
                          trade.actual_risk_reward_ratio >= 2 ? 'text-green-400' :
                          trade.actual_risk_reward_ratio >= 1 ? 'text-yellow-400' :
                          'text-red-400'
                        }`}>
                          {trade.actual_risk_reward_ratio.toFixed(2)}:1
                        </span>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </td>
                  )}
                  <td className="py-1 px-2 text-green-300">
                    ¥{(trade.buy_commission !== undefined && trade.buy_commission !== null ? trade.buy_commission : trade.commission).toFixed(2)}
                  </td>
                  {viewMode === 'all' && (
                    <td className="py-1 px-2 text-red-300">
                      {trade.sell_commission !== undefined && trade.sell_commission !== null && trade.sell_commission > 0 ? (
                        `¥${trade.sell_commission.toFixed(2)}`
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </td>
                  )}
                  <td className="py-1 px-2 text-yellow-300 font-semibold">¥{trade.commission.toFixed(2)}</td>
                  {viewMode === 'all' && (
                    <td className="py-1 px-2">
                      <span className={`inline-block min-w-[48px] text-center px-1 py-0.5 rounded text-xs ${
                        trade.order_result === '止盈' ? 'bg-green-500/20 text-green-400' :
                        trade.order_result === '止损' ? 'bg-red-500/20 text-red-400' :
                        trade.status === 'open' ? 'bg-blue-500/20 text-blue-400' :
                        'bg-gray-500/20 text-gray-400'
                      }`}>
                        {trade.order_result || (trade.status === 'open' ? '持仓中' : '已平仓')}
                      </span>
                    </td>
                  )}
                  {viewMode === 'all' && (
                    <td className="py-1 px-2">
                      {trade.profit_loss !== undefined && trade.profit_loss !== null ? (
                        <span className={`font-bold ${
                          trade.profit_loss > 0 ? 'text-green-400' :
                          trade.profit_loss < 0 ? 'text-red-400' :
                          'text-gray-400'
                        }`}>
                          {trade.profit_loss > 0 ? '+' : ''}¥{trade.profit_loss.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-gray-500 text-xs">-</span>
                      )}
                    </td>
                  )}
                  <td className="py-1 px-2">
                    {/* 只有持仓中才显示出场闹铃，已平仓不显示 */}
                    {trade.status === 'open' ? (
                      <div className="flex space-x-1">
                        {trade.stop_loss_alert && (
                          <span className="px-1 py-0.5 bg-red-500/20 text-red-400 rounded text-xs">止损</span>
                        )}
                        {trade.take_profit_alert && (
                          <span className="px-1 py-0.5 bg-green-500/20 text-green-400 rounded text-xs">止盈</span>
                        )}
                      </div>
                    ) : (
                      <span className="text-gray-500 text-xs">-</span>
                    )}
                  </td>
                  <td className="py-1 px-2 min-w-[72px]">
                    {/* 竖排避免在窄屏/被裁剪时看不到“删除”按钮 */}
                    <div className="flex flex-col items-center gap-1">
                      <button
                        onClick={() => handleEdit(trade)}
                        className="px-2 py-1 rounded hover:bg-jojo-gold/20 text-jojo-gold hover:text-jojo-gold-dark transition-all flex items-center gap-1 text-xs"
                        title="编辑交易"
                      >
                        <Edit size={14} />
                        <span>编辑</span>
                      </button>
                      <button
                        onClick={() => handleDelete(trade.id)}
                        className="px-2 py-1 rounded hover:bg-red-500/20 text-red-400 hover:text-red-300 transition-all flex items-center gap-1 text-xs"
                        title="删除交易（资金将重新计算）"
                      >
                        <Trash2 size={14} />
                        <span>删除</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      
      {/* 分页控件 - 仅在全部历史模式下显示 */}
      {viewMode === 'all' && totalPages > 0 && (
        <div className="flex items-center justify-between mt-3 px-2 py-1 bg-jojo-blue-light rounded border border-jojo-gold/30">
          <div className="text-xs text-gray-300">
            共 <span className="text-jojo-gold font-bold">{totalItems}</span> 条记录
            <span className="mx-2 text-gray-600">|</span>
            第 <span className="text-white font-bold">{page}</span> / {totalPages} 页
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              className={`px-3 py-1 text-xs rounded transition-all ${
                page <= 1 || loading
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-jojo-blue border border-jojo-gold text-jojo-gold hover:bg-jojo-gold hover:text-jojo-blue'
              }`}
            >
              上一页
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className={`px-3 py-1 text-xs rounded transition-all ${
                page >= totalPages || loading
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-jojo-blue border border-jojo-gold text-jojo-gold hover:bg-jojo-gold hover:text-jojo-blue'
              }`}
            >
              下一页
            </button>
          </div>
        </div>
      )}

      {/* JOJO风格弹窗 */}
      <Modal />
    </div>
  );
}
