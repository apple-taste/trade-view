import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useForex, type ForexTrade, type ForexSide, type ForexQuote } from '../../contexts/ForexContext';
import { useLocale } from '../../contexts/LocaleContext';
import { Plus, X, Edit, Trash2, CheckCircle2 } from 'lucide-react';
import { useJojoModal } from '../JojoModal';
import { useTrade } from '../../contexts/TradeContext';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

type ActiveTab = 'OPEN' | 'CLOSED';

const contractSize = (symbol: string) => {
  return symbol.trim().toUpperCase() === 'XAUUSD' ? 100 : 100000;
};

const floorToStep = (value: number, step: number) => {
  if (!Number.isFinite(value) || !Number.isFinite(step) || step <= 0) return NaN;
  return Math.floor(value / step) * step;
};

const calcLotsFromRisk = (params: { riskAmount: number; openPrice: number; slPrice: number; symbol: string }) => {
  const { riskAmount, openPrice, slPrice, symbol } = params;
  if (!Number.isFinite(riskAmount) || riskAmount <= 0) return null;
  if (!Number.isFinite(openPrice) || openPrice <= 0) return null;
  if (!Number.isFinite(slPrice) || slPrice <= 0) return null;
  const riskPerLot = Math.abs(openPrice - slPrice) * contractSize(symbol);
  if (!Number.isFinite(riskPerLot) || riskPerLot <= 0) return null;
  const rawLots = riskAmount / riskPerLot;
  if (!Number.isFinite(rawLots) || rawLots <= 0) return null;
  const step = 0.0001;
  const flooredLots = floorToStep(rawLots, step);
  if (!Number.isFinite(flooredLots) || flooredLots < 0) return null;
  const safeLots = flooredLots > 0 ? flooredLots : step;
  return safeLots.toFixed(4);
};

const toLocalDateTimeInputValue = (d: Date) => {
  const offsetMs = d.getTimezoneOffset() * 60_000;
  return new Date(d.getTime() - offsetMs).toISOString().slice(0, 16);
};

const fromLocalDateTimeInputToIso = (value: string) => {
  if (!value) return undefined;
  return new Date(value).toISOString();
};

const displayTime = (value?: string | null) => {
  if (!value) return '-';
  return value.replace('T', ' ').replace('Z', '').split('.')[0];
};

export default function ForexTerminal() {
  const { account, openTrades, closedTrades, createTrade, closeTrade, updateTrade, deleteTrade, clearAllTrades, fetchQuotes, refresh } = useForex();
  const { t } = useLocale();
  const { confirm: jojoConfirm, prompt: jojoPrompt, Modal } = useJojoModal();
  const { forexStrategies, effectiveForexStrategyId, setCurrentForexStrategyId, createForexStrategy, deleteForexStrategy, deleteAllForexStrategies } = useTrade();
  const navigate = useNavigate();
  const { refreshBillingStatus } = useAuth();
  const [activeTab, setActiveTab] = useState<ActiveTab>('OPEN');
  const [createOpen, setCreateOpen] = useState(false);
  const [closeTarget, setCloseTarget] = useState<ForexTrade | null>(null);
  const [editTarget, setEditTarget] = useState<ForexTrade | null>(null);
  const [lotsManuallySet, setLotsManuallySet] = useState(false);
  const [liveQuote, setLiveQuote] = useState<ForexQuote | null>(null);

  const [createForm, setCreateForm] = useState(() => ({
    symbol: 'EURUSD',
    side: 'BUY' as ForexSide,
    lots: '0.01',
    openTime: toLocalDateTimeInputValue(new Date()),
    openPrice: '',
    sl: '',
    stopLossAmount: '',
    tp: '',
    commission: '0',
    swap: '0',
    notes: '',
  }));

  const [closeForm, setCloseForm] = useState(() => ({
    closeTime: toLocalDateTimeInputValue(new Date()),
    closePrice: '',
    commission: '',
    swap: '',
  }));

  const [editForm, setEditForm] = useState(() => ({
    sl: '',
    tp: '',
    notes: '',
  }));

  const realizedProfit = useMemo(() => {
    return closedTrades.reduce((sum, t) => sum + Number(t.profit ?? 0), 0);
  }, [closedTrades]);

  const openRows = useMemo(() => {
    return [...openTrades].sort((a, b) => (a.openTime < b.openTime ? 1 : -1));
  }, [openTrades]);

  const closedRows = useMemo(() => {
    return [...closedTrades].sort((a, b) => ((a.closeTime ?? a.openTime) < (b.closeTime ?? b.openTime) ? 1 : -1));
  }, [closedTrades]);

  useEffect(() => {
    let active = true;
    if (!createOpen) {
      setLiveQuote(null);
      return () => {};
    }
    const sym = createForm.symbol.trim();
    if (!sym) {
      setLiveQuote(null);
      return () => {};
    }

    const tick = async () => {
      try {
        const res = await fetchQuotes([sym]);
        if (!active) return;
        setLiveQuote(res[0] ?? null);
      } catch {
        if (!active) return;
        setLiveQuote(null);
      }
    };

    tick();
    const id = window.setInterval(tick, 2000);
    return () => {
      active = false;
      window.clearInterval(id);
    };
  }, [createForm.symbol, createOpen, fetchQuotes]);

  const computedRiskPreview = useMemo(() => {
    const riskAmount = Number(createForm.stopLossAmount);
    const openPrice = Number(createForm.openPrice);
    const slPrice = Number(createForm.sl);
    if (!Number.isFinite(riskAmount) || riskAmount <= 0) return null;
    if (!Number.isFinite(openPrice) || openPrice <= 0) return null;
    if (!Number.isFinite(slPrice) || slPrice <= 0) return null;
    const lots = calcLotsFromRisk({ riskAmount, openPrice, slPrice, symbol: createForm.symbol });
    if (!lots) return null;
    return { riskAmount, openPrice, slPrice, lots, contractSize: contractSize(createForm.symbol) };
  }, [createForm.openPrice, createForm.sl, createForm.stopLossAmount, createForm.symbol]);

  const computedMarginPreview = useMemo(() => {
    const lots = Number(createForm.lots);
    const openPrice = Number(createForm.openPrice);
    const leverage = Number(account.leverage || 0);
    if (!Number.isFinite(lots) || lots <= 0) return null;
    if (!Number.isFinite(openPrice) || openPrice <= 0) return null;
    if (!Number.isFinite(leverage) || leverage <= 0) return null;
    const notional = lots * contractSize(createForm.symbol) * openPrice;
    if (!Number.isFinite(notional) || notional <= 0) return null;
    const margin = notional / leverage;
    if (!Number.isFinite(margin) || margin < 0) return null;
    return { margin, leverage };
  }, [account.leverage, createForm.lots, createForm.openPrice, createForm.symbol]);

  const handleCreate = async () => {
    try {
      const lots = Number(createForm.lots);
      const openPrice = Number(createForm.openPrice);
      if (!createForm.symbol.trim()) throw new Error('Symbol required');
      if (!Number.isFinite(lots) || lots <= 0) throw new Error('Invalid lots');
      if (!Number.isFinite(openPrice) || openPrice <= 0) throw new Error('Invalid open price');

      await createTrade({
        symbol: createForm.symbol.trim().toUpperCase(),
        side: createForm.side,
        lots,
        open_time: fromLocalDateTimeInputToIso(createForm.openTime),
        open_price: openPrice,
        sl: createForm.sl ? Number(createForm.sl) : undefined,
        tp: createForm.tp ? Number(createForm.tp) : undefined,
        commission: createForm.commission ? Number(createForm.commission) : undefined,
        swap: createForm.swap ? Number(createForm.swap) : undefined,
        notes: createForm.notes ? createForm.notes : undefined,
      });
      setCreateOpen(false);
      await refresh();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const status = err?.response?.status;
      const billingRequired =
        status === 403 &&
        (detail?.code === 'BILLING_REQUIRED' ||
          (typeof detail === 'string' && detail.includes('BILLING_REQUIRED')));
      if (billingRequired) {
        const msg =
          (typeof detail === 'object' && detail?.message) ||
          (typeof detail === 'string' ? detail : '') ||
          '非Pro会员无法新增交易记录，请先开通Pro会员';
        const ok = await jojoConfirm('需要会员', msg);
        if (ok) {
          await refreshBillingStatus();
          navigate('/billing?months=1');
        }
        return;
      }

      const msg =
        (typeof detail === 'object' && detail?.message) ||
        (typeof detail === 'string' ? detail : '') ||
        err?.message ||
        '操作失败';
      alert(msg);
    }
  };

  const handleOpenClose = (trade: ForexTrade) => {
    setCloseTarget(trade);
    setCloseForm({
      closeTime: toLocalDateTimeInputValue(new Date()),
      closePrice: '',
      commission: '',
      swap: '',
    });
  };

  const handleClose = async () => {
    if (!closeTarget) return;
    try {
      const closePrice = Number(closeForm.closePrice);
      if (!Number.isFinite(closePrice) || closePrice <= 0) throw new Error('Invalid close price');
      await closeTrade(closeTarget.id, {
        close_time: fromLocalDateTimeInputToIso(closeForm.closeTime),
        close_price: closePrice,
        commission: closeForm.commission ? Number(closeForm.commission) : undefined,
        swap: closeForm.swap ? Number(closeForm.swap) : undefined,
      });
      setCloseTarget(null);
      await refresh();
    } catch (err: any) {
      alert(err?.response?.data?.detail || err?.message || '操作失败');
    }
  };

  const handleOpenEdit = (trade: ForexTrade) => {
    setEditTarget(trade);
    setEditForm({
      sl: trade.sl != null ? String(trade.sl) : '',
      tp: trade.tp != null ? String(trade.tp) : '',
      notes: trade.notes ?? '',
    });
  };

  const handleEdit = async () => {
    if (!editTarget) return;
    try {
      await updateTrade(editTarget.id, {
        sl: editForm.sl ? Number(editForm.sl) : undefined,
        tp: editForm.tp ? Number(editForm.tp) : undefined,
        notes: editForm.notes,
      });
      setEditTarget(null);
      await refresh();
    } catch (err: any) {
      alert(err?.response?.data?.detail || err?.message || '操作失败');
    }
  };

  const handleDelete = async (tradeId: number) => {
    if (!window.confirm('确定删除该记录？')) return;
    try {
      await deleteTrade(tradeId);
      await refresh();
    } catch (err: any) {
      alert(err?.response?.data?.detail || err?.message || '操作失败');
    }
  };

  const handleClearAll = async () => {
    const total = openTrades.length + closedTrades.length;
    if (total === 0) return;

    const first = await jojoConfirm(
      '⚠️ 清空所有交易记录',
      `此操作将：\n• 删除所有交易记录（软删除）\n• 清除所有持仓记录\n• 资金曲线恢复到初始资金锚点\n\n此操作不可恢复！`
    );
    if (!first) return;

    const second = await jojoConfirm(
      '⚠️ 最终确认',
      `最后确认：真的要清空所有交易记录吗？\n\n清空后，总资产将恢复到初始资金状态。`
    );
    if (!second) return;

    try {
      const res = await clearAllTrades();
      await new Promise((r) => setTimeout(r, 400));
      alert(`✅ 已清空交易记录\n\n删除数量：${res.deleted_count}\n💡 总资产已恢复到初始资金状态`);
      await refresh();
    } catch (err: any) {
      alert(err?.response?.data?.detail || err?.message || '清空失败，请稍后重试');
    }
  };

  const handleCreateStrategy = async () => {
    const name = await jojoPrompt('✨ 新建策略', '请输入策略名称');
    if (!name) return;
    const created = await createForexStrategy(name);
    if (!created?.id) return;
    setCurrentForexStrategyId(created.id);
  };

  const handleDeleteCurrentStrategy = async () => {
    const current =
      effectiveForexStrategyId != null ? forexStrategies.find((s) => s.id === effectiveForexStrategyId) : null;
    if (!current) return;
    const ok = await jojoConfirm('🗑️ 删除策略', `确定删除策略「${current.name}」吗？\n\n删除后将软删除该策略下所有外汇交易记录。`);
    if (!ok) return;
    await deleteForexStrategy(current.id);
  };

  const handleClearAllStrategies = async () => {
    if (forexStrategies.length === 0) return;
    
    const first = await jojoConfirm(
      '⚠️ 清空所有策略',
      `确定要删除所有外汇策略吗？\n\n此操作将：\n• 删除所有外汇策略\n• 清空所有外汇交易记录\n• 资金曲线重置\n\n此操作不可恢复！`
    );
    if (!first) return;

    const second = await jojoConfirm(
      '⚠️ 最终确认',
      `请再次确认：您真的要清空所有外汇策略吗？`
    );
    if (!second) return;

    try {
      await deleteAllForexStrategies();
      alert('✅ 已清空所有外汇策略');
    } catch (err: any) {
      alert(err?.response?.data?.detail || err?.message || '操作失败');
    }
  };

  return (
    <div className="h-full bg-gray-800 rounded-lg border border-gray-700 flex flex-col overflow-hidden">
      <div className="p-2 bg-gray-900 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 mr-2">
            <select
              value={effectiveForexStrategyId ?? ''}
              onChange={(e) => {
                const raw = e.target.value;
                setCurrentForexStrategyId(raw ? Number(raw) : null);
              }}
              className="px-2 py-1 text-xs font-bold rounded bg-gray-800 border border-gray-700 text-gray-200 focus:outline-none focus:ring-1 focus:ring-jojo-gold"
            >
              <option value="">请选择策略</option>
              {forexStrategies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
            <button
              onClick={handleCreateStrategy}
              className="px-2 py-1 text-xs font-bold rounded bg-jojo-gold text-gray-900 hover:bg-yellow-400 transition-colors"
            >
              新建
            </button>
            <button
              onClick={handleDeleteCurrentStrategy}
              disabled={effectiveForexStrategyId == null}
              className={`px-2 py-1 text-xs font-bold rounded transition-colors ${
                effectiveForexStrategyId == null
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-red-500/20 text-red-300 hover:bg-red-500/30'
              }`}
            >
              删除
            </button>
            {forexStrategies.length > 0 && (
              <button
                onClick={handleClearAllStrategies}
                className="px-2 py-1 text-xs font-bold rounded transition-colors bg-red-900/50 text-red-400 hover:bg-red-900 border border-red-800"
                title="清空所有策略"
              >
                清空
              </button>
            )}
          </div>
          <button
            onClick={() => setActiveTab('OPEN')}
            className={`px-3 py-1 text-xs font-bold rounded transition-colors ${
              activeTab === 'OPEN' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            {t('forex.tab.positions')} ({openTrades.length})
          </button>
          <button
            onClick={() => setActiveTab('CLOSED')}
            className={`px-3 py-1 text-xs font-bold rounded transition-colors ${
              activeTab === 'CLOSED' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            {t('forex.tab.history')} ({closedTrades.length})
          </button>
          <span className="text-xs text-gray-500 ml-2">
            {t('forex.totalProfit')}: <span className={realizedProfit >= 0 ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>{realizedProfit.toFixed(2)}</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleClearAll}
            disabled={openTrades.length + closedTrades.length === 0}
            className={`px-3 py-1 text-xs font-bold rounded transition-colors flex items-center gap-1 ${
              openTrades.length + closedTrades.length === 0
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-red-500/20 text-red-300 hover:bg-red-500/30'
            }`}
            title={t('forex.clearAllTrades')}
          >
            <Trash2 size={14} /> {t('forex.clearAllTrades')}
          </button>
          <button
            onClick={async () => {
              try {
                const res = await axios.get('/api/user/billing-status');
                const bs = res.data;
                if (bs?.billing_enabled && !bs?.is_paid) {
                  const ok = await jojoConfirm('需要会员', '非Pro会员无法新增交易记录，请先开通Pro会员');
                  if (ok) {
                    await refreshBillingStatus();
                    navigate('/billing?months=1');
                  }
                  return;
                }
              } catch {
              }
              setCreateOpen(true);
            }}
            className="px-3 py-1 text-xs font-bold rounded bg-jojo-gold text-gray-900 hover:bg-yellow-400 transition-colors flex items-center gap-1"
          >
            <Plus size={14} /> {t('forex.addTrade')}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto custom-scrollbar">
        {activeTab === 'OPEN' && (
          <table className="w-full text-left text-xs md:text-sm">
            <thead className="bg-gray-900/50 sticky top-0 text-gray-500">
              <tr>
                <th className="p-2">开仓时间</th>
                <th className="p-2">品种</th>
                <th className="p-2">方向</th>
                <th className="p-2">手数</th>
                <th className="p-2">开仓价</th>
                <th className="p-2 hidden md:table-cell">S/L</th>
                <th className="p-2 hidden md:table-cell">T/P</th>
                <th className="p-2 hidden md:table-cell">手续费</th>
                <th className="p-2 hidden md:table-cell">隔夜</th>
                <th className="p-2 text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              {openRows.map((trade) => (
                <tr key={trade.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                  <td className="p-2 text-gray-500">{displayTime(trade.openTime)}</td>
                  <td className="p-2 font-bold text-gray-200">{trade.symbol}</td>
                  <td className={`p-2 font-bold ${trade.side === 'BUY' ? 'text-blue-400' : 'text-red-400'}`}>{trade.side}</td>
                  <td className="p-2">{trade.lots}</td>
                  <td className="p-2 font-mono">{trade.openPrice.toFixed(5)}</td>
                  <td className="p-2 hidden md:table-cell text-red-400/70">{trade.sl ?? '-'}</td>
                  <td className="p-2 hidden md:table-cell text-green-400/70">{trade.tp ?? '-'}</td>
                  <td className="p-2 hidden md:table-cell text-red-400/70">{trade.commission.toFixed(2)}</td>
                  <td className="p-2 hidden md:table-cell text-gray-400">{trade.swap.toFixed(2)}</td>
                  <td className="p-2 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleOpenClose(trade)}
                        className="px-2 py-1 rounded hover:bg-green-500/20 text-green-400 hover:text-green-300 transition-all flex items-center gap-1 text-xs"
                        title={t('forex.closeTrade')}
                      >
                        <CheckCircle2 size={14} />
                        <span>平仓</span>
                      </button>
                      <button
                        onClick={() => handleOpenEdit(trade)}
                        className="px-2 py-1 rounded hover:bg-jojo-gold/20 text-jojo-gold hover:text-jojo-gold-dark transition-all flex items-center gap-1 text-xs"
                        title={t('forex.editTrade')}
                      >
                        <Edit size={14} />
                        <span>编辑</span>
                      </button>
                      <button
                        onClick={() => handleDelete(trade.id)}
                        className="px-2 py-1 rounded hover:bg-red-500/20 text-red-400 hover:text-red-300 transition-all flex items-center gap-1 text-xs"
                        title={t('forex.deleteTrade')}
                      >
                        <Trash2 size={14} />
                        <span>删除</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {openRows.length === 0 && (
                <tr><td colSpan={10} className="p-4 text-center text-gray-500">{t('forex.noHistory')}</td></tr>
              )}
            </tbody>
          </table>
        )}

        {activeTab === 'CLOSED' && (
          <table className="w-full text-left text-xs md:text-sm">
            <thead className="bg-gray-900/50 sticky top-0 text-gray-500">
              <tr>
                <th className="p-2">平仓时间</th>
                <th className="p-2">品种</th>
                <th className="p-2">方向</th>
                <th className="p-2">手数</th>
                <th className="p-2 hidden md:table-cell">开仓价</th>
                <th className="p-2 hidden md:table-cell">平仓价</th>
                <th className="p-2 hidden md:table-cell">理论 R:R</th>
                <th className="p-2 hidden md:table-cell">实际 R:R</th>
                <th className="p-2 hidden md:table-cell">手续费</th>
                <th className="p-2 hidden md:table-cell">隔夜</th>
                <th className="p-2">盈亏</th>
                <th className="p-2 text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              {closedRows.map((trade) => (
                <tr key={trade.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                  <td className="p-2 text-gray-500">{displayTime(trade.closeTime ?? trade.openTime)}</td>
                  <td className="p-2 font-bold text-gray-200">{trade.symbol}</td>
                  <td className={`p-2 font-bold ${trade.side === 'BUY' ? 'text-blue-400' : 'text-red-400'}`}>{trade.side}</td>
                  <td className="p-2">{trade.lots}</td>
                  <td className="p-2 hidden md:table-cell font-mono">{trade.openPrice.toFixed(5)}</td>
                  <td className="p-2 hidden md:table-cell font-mono">{trade.closePrice != null ? trade.closePrice.toFixed(5) : '-'}</td>
                  <td className="p-2 hidden md:table-cell text-gray-400">
                    {trade.theoreticalRiskRewardRatio != null ? `1:${trade.theoreticalRiskRewardRatio.toFixed(2)}` : '-'}
                  </td>
                  <td className={`p-2 hidden md:table-cell font-bold ${Number(trade.actualRiskRewardRatio ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {trade.actualRiskRewardRatio != null ? `1:${trade.actualRiskRewardRatio.toFixed(2)}` : '-'}
                  </td>
                  <td className="p-2 hidden md:table-cell text-red-400/70">{trade.commission.toFixed(2)}</td>
                  <td className="p-2 hidden md:table-cell text-gray-400">{trade.swap.toFixed(2)}</td>
                  <td className={`p-2 font-bold ${Number(trade.profit ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {trade.profit != null ? trade.profit.toFixed(2) : '-'}
                  </td>
                  <td className="p-2 text-right">
                    <button
                      onClick={() => handleDelete(trade.id)}
                      className="px-2 py-1 rounded hover:bg-red-500/20 text-red-400 hover:text-red-300 transition-all flex items-center gap-1 text-xs ml-auto"
                      title={t('forex.deleteTrade')}
                    >
                      <Trash2 size={14} />
                      <span>删除</span>
                    </button>
                  </td>
                </tr>
              ))}
              {closedRows.length === 0 && (
                <tr><td colSpan={10} className="p-4 text-center text-gray-500">{t('forex.noHistory')}</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {createOpen && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg shadow-2xl w-full max-w-2xl border border-gray-700">
            <div className="p-4 border-b border-gray-700 flex justify-between items-center bg-gray-900">
              <h2 className="text-lg font-bold text-jojo-gold">{t('forex.addTrade')}</h2>
              <button onClick={() => setCreateOpen(false)} className="text-gray-400 hover:text-white">
                <X size={20} />
              </button>
            </div>
            <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-gray-200">
              <div>
                <label className="block text-xs text-gray-400 mb-1">品种</label>
                <input
                  value={createForm.symbol}
                  onChange={(e) => {
                    const nextSymbol = e.target.value;
                    setCreateForm((p) => {
                      const next = { ...p, symbol: nextSymbol };
                      if (lotsManuallySet) return next;
                      if (!p.stopLossAmount) return next;
                      const lots = calcLotsFromRisk({
                        riskAmount: Number(p.stopLossAmount),
                        openPrice: Number(p.openPrice),
                        slPrice: Number(p.sl),
                        symbol: nextSymbol,
                      });
                      return lots ? { ...next, lots } : next;
                    });
                  }}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
                {liveQuote?.price != null && (
                  <div className="mt-1 flex items-center justify-between gap-2 text-[11px] text-gray-400">
                    <span className="font-mono">现价 {Number(liveQuote.price).toFixed(5)}</span>
                    <button
                      type="button"
                      onClick={() => {
                        if (liveQuote.price == null) return;
                        setLotsManuallySet(false);
                        setCreateForm((p) => {
                          const next = { ...p, openPrice: String(liveQuote.price) };
                          if (!p.stopLossAmount) return next;
                          const lots = calcLotsFromRisk({
                            riskAmount: Number(p.stopLossAmount),
                            openPrice: Number(liveQuote.price),
                            slPrice: Number(p.sl),
                            symbol: p.symbol,
                          });
                          return lots ? { ...next, lots } : next;
                        });
                      }}
                      className="px-2 py-0.5 rounded bg-gray-700 hover:bg-gray-600 text-gray-200"
                    >
                      填入
                    </button>
                  </div>
                )}
                {liveQuote?.source && <div className="mt-1 text-[11px] text-gray-500">来源：{liveQuote.source}</div>}
                {liveQuote?.error && <div className="mt-1 text-[11px] text-red-400">{liveQuote.error}</div>}
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">方向</label>
                <select
                  value={createForm.side}
                  onChange={(e) => setCreateForm((p) => ({ ...p, side: e.target.value as ForexSide }))}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                >
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">开仓时间</label>
                <input
                  type="datetime-local"
                  value={createForm.openTime}
                  onChange={(e) => setCreateForm((p) => ({ ...p, openTime: e.target.value }))}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">手数</label>
                <input
                  value={createForm.lots}
                  onChange={(e) => {
                    setLotsManuallySet(true);
                    setCreateForm((p) => ({ ...p, lots: e.target.value }));
                  }}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">开仓价</label>
                <input
                  value={createForm.openPrice}
                  onChange={(e) => {
                    const nextOpenPrice = e.target.value;
                    setCreateForm((p) => {
                      const next = { ...p, openPrice: nextOpenPrice };
                      if (lotsManuallySet) return next;
                      if (!p.stopLossAmount) return next;
                      const lots = calcLotsFromRisk({
                        riskAmount: Number(p.stopLossAmount),
                        openPrice: Number(nextOpenPrice),
                        slPrice: Number(p.sl),
                        symbol: p.symbol,
                      });
                      return lots ? { ...next, lots } : next;
                    });
                  }}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none font-mono"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">手续费</label>
                <input
                  value={createForm.commission}
                  onChange={(e) => setCreateForm((p) => ({ ...p, commission: e.target.value }))}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">{t('forex.stopLoss')}</label>
                <input
                  value={createForm.sl}
                  onChange={(e) => {
                    const nextSl = e.target.value;
                    setCreateForm((p) => {
                      const next = { ...p, sl: nextSl };
                      if (lotsManuallySet) return next;
                      if (!p.stopLossAmount) return next;
                      const lots = calcLotsFromRisk({
                        riskAmount: Number(p.stopLossAmount),
                        openPrice: Number(p.openPrice),
                        slPrice: Number(nextSl),
                        symbol: p.symbol,
                      });
                      return lots ? { ...next, lots } : next;
                    });
                  }}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">单笔止损金额</label>
                <input
                  type="number"
                  step="0.01"
                  value={createForm.stopLossAmount}
                  onChange={(e) => {
                    const nextRisk = e.target.value;
                    setLotsManuallySet(false);
                    setCreateForm((p) => {
                      const next = { ...p, stopLossAmount: nextRisk };
                      const lots = calcLotsFromRisk({
                        riskAmount: Number(nextRisk),
                        openPrice: Number(p.openPrice),
                        slPrice: Number(p.sl),
                        symbol: p.symbol,
                      });
                      return lots ? { ...next, lots } : next;
                    });
                  }}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
                {computedRiskPreview && (
                  <div className="mt-1 text-[11px] text-gray-400">
                    合约大小 {computedRiskPreview.contractSize}，自动手数 {computedRiskPreview.lots}
                  </div>
                )}
                {computedMarginPreview && (
                  <div className="mt-1 text-[11px] text-gray-400">
                    估算保证金 {computedMarginPreview.margin.toFixed(2)}（1:{computedMarginPreview.leverage}）
                  </div>
                )}
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">{t('forex.takeProfit')}</label>
                <input
                  value={createForm.tp}
                  onChange={(e) => setCreateForm((p) => ({ ...p, tp: e.target.value }))}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">隔夜</label>
                <input
                  value={createForm.swap}
                  onChange={(e) => setCreateForm((p) => ({ ...p, swap: e.target.value }))}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs text-gray-400 mb-1">备注</label>
                <input
                  value={createForm.notes}
                  onChange={(e) => setCreateForm((p) => ({ ...p, notes: e.target.value }))}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
              </div>
            </div>
            <div className="p-4 border-t border-gray-700 bg-gray-900 flex justify-end gap-2">
              <button onClick={() => setCreateOpen(false)} className="px-4 py-2 text-gray-400 hover:text-white transition-colors">
                {t('forex.cancel')}
              </button>
              <button
                onClick={handleCreate}
                className="px-6 py-2 bg-jojo-gold text-gray-900 font-bold rounded hover:bg-yellow-400 transition-colors"
              >
                {t('forex.save')}
              </button>
            </div>
          </div>
        </div>
      )}

      {closeTarget && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg shadow-2xl w-full max-w-xl border border-gray-700">
            <div className="p-4 border-b border-gray-700 flex justify-between items-center bg-gray-900">
              <h2 className="text-lg font-bold text-jojo-gold">{t('forex.closeTrade')}</h2>
              <button onClick={() => setCloseTarget(null)} className="text-gray-400 hover:text-white">
                <X size={20} />
              </button>
            </div>
            <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-gray-200">
              <div>
                <label className="block text-xs text-gray-400 mb-1">平仓时间</label>
                <input
                  type="datetime-local"
                  value={closeForm.closeTime}
                  onChange={(e) => setCloseForm((p) => ({ ...p, closeTime: e.target.value }))}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">平仓价</label>
                <input
                  value={closeForm.closePrice}
                  onChange={(e) => setCloseForm((p) => ({ ...p, closePrice: e.target.value }))}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none font-mono"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">手续费</label>
                <input
                  value={closeForm.commission}
                  onChange={(e) => setCloseForm((p) => ({ ...p, commission: e.target.value }))}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">隔夜</label>
                <input
                  value={closeForm.swap}
                  onChange={(e) => setCloseForm((p) => ({ ...p, swap: e.target.value }))}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
              </div>
            </div>
            <div className="p-4 border-t border-gray-700 bg-gray-900 flex justify-end gap-2">
              <button onClick={() => setCloseTarget(null)} className="px-4 py-2 text-gray-400 hover:text-white transition-colors">
                {t('forex.cancel')}
              </button>
              <button
                onClick={handleClose}
                className="px-6 py-2 bg-green-500 text-gray-900 font-bold rounded hover:bg-green-400 transition-colors"
              >
                {t('forex.closeTrade')}
              </button>
            </div>
          </div>
        </div>
      )}

      {editTarget && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg shadow-2xl w-full max-w-xl border border-gray-700">
            <div className="p-4 border-b border-gray-700 flex justify-between items-center bg-gray-900">
              <h2 className="text-lg font-bold text-jojo-gold">{t('forex.editTrade')}</h2>
              <button onClick={() => setEditTarget(null)} className="text-gray-400 hover:text-white">
                <X size={20} />
              </button>
            </div>
            <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-gray-200">
              <div>
                <label className="block text-xs text-gray-400 mb-1">{t('forex.stopLoss')}</label>
                <input
                  value={editForm.sl}
                  onChange={(e) => setEditForm((p) => ({ ...p, sl: e.target.value }))}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">{t('forex.takeProfit')}</label>
                <input
                  value={editForm.tp}
                  onChange={(e) => setEditForm((p) => ({ ...p, tp: e.target.value }))}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs text-gray-400 mb-1">备注</label>
                <input
                  value={editForm.notes}
                  onChange={(e) => setEditForm((p) => ({ ...p, notes: e.target.value }))}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 outline-none"
                />
              </div>
            </div>
            <div className="p-4 border-t border-gray-700 bg-gray-900 flex justify-end gap-2">
              <button onClick={() => setEditTarget(null)} className="px-4 py-2 text-gray-400 hover:text-white transition-colors">
                {t('forex.cancel')}
              </button>
              <button
                onClick={handleEdit}
                className="px-6 py-2 bg-jojo-gold text-gray-900 font-bold rounded hover:bg-yellow-400 transition-colors"
              >
                {t('forex.save')}
              </button>
            </div>
          </div>
        </div>
      )}
      <Modal />
    </div>
  );
}
