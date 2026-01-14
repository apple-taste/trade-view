import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from 'react';
import axios from 'axios';

export type ForexSide = 'BUY' | 'SELL';
export type ForexTradeStatus = 'open' | 'closed';

export interface ForexAccount {
  currency: string;
  leverage: number;
  initialBalance: number;
  initialDate?: string | null;
  balance: number;
  equity: number;
  margin: number;
  freeMargin: number;
  marginLevel: number;
  maxDrawdown: number;
  peakEquity: number;
}

export interface ForexTrade {
  id: number;
  symbol: string;
  side: ForexSide;
  lots: number;
  openTime: string;
  closeTime?: string | null;
  openPrice: number;
  closePrice?: number | null;
  sl?: number;
  tp?: number;
  commission: number;
  swap: number;
  profit?: number | null;
  notes?: string | null;
  status: ForexTradeStatus;
}

export interface ForexCapitalPoint {
  date: string;
  equity: number;
  balance: number;
}

export interface ForexQuote {
  symbol: string;
  price: number | null;
  bid: number | null;
  ask: number | null;
  asof: string;
  source: string;
  error?: string | null;
}

export type ForexTradeCreatePayload = {
  symbol: string;
  side: ForexSide;
  lots: number;
  open_time?: string;
  open_price: number;
  sl?: number;
  tp?: number;
  commission?: number;
  swap?: number;
  notes?: string;
};

export type ForexTradeClosePayload = {
  close_time?: string;
  close_price: number;
  commission?: number;
  swap?: number;
};

export type ForexTradeUpdatePayload = {
  sl?: number;
  tp?: number;
  notes?: string;
};

export type ForexAccountUpdatePayload = {
  currency?: string;
  leverage?: number;
};

export type ForexInitialCapitalPayload = {
  initial_balance: number;
  initial_date?: string;
};

export type ForexAccountResetPayload = {
  balance: number;
  date?: string;
  currency?: string;
  leverage?: number;
};

interface ForexContextType {
  account: ForexAccount;
  openTrades: ForexTrade[];
  closedTrades: ForexTrade[];
  capitalHistory: ForexCapitalPoint[];
  refreshKey: number;

  createTrade: (payload: ForexTradeCreatePayload) => Promise<void>;
  closeTrade: (tradeId: number, payload: ForexTradeClosePayload) => Promise<void>;
  updateTrade: (tradeId: number, payload: ForexTradeUpdatePayload) => Promise<void>;
  deleteTrade: (tradeId: number) => Promise<void>;
  clearAllTrades: () => Promise<{ deleted_count: number }>;
  updateAccount: (payload: ForexAccountUpdatePayload) => Promise<void>;
  setInitialCapital: (payload: ForexInitialCapitalPayload) => Promise<void>;
  resetAccount: (payload: ForexAccountResetPayload) => Promise<void>;
  fetchQuotes: (symbols: string[]) => Promise<ForexQuote[]>;
  refresh: () => Promise<void>;
}

const ForexContext = createContext<ForexContextType | undefined>(undefined);

const mapAccount = (data: any): ForexAccount => {
  return {
    currency: String(data.currency ?? 'USD'),
    leverage: Number(data.leverage ?? 0),
    initialBalance: Number(data.initial_balance ?? 0),
    initialDate: data.initial_date != null ? String(data.initial_date) : null,
    balance: Number(data.balance ?? 0),
    equity: Number(data.equity ?? data.balance ?? 0),
    margin: Number(data.margin ?? 0),
    freeMargin: Number(data.free_margin ?? data.freeMargin ?? 0),
    marginLevel: Number(data.margin_level ?? data.marginLevel ?? 0),
    maxDrawdown: Number(data.max_drawdown ?? data.maxDrawdown ?? 0),
    peakEquity: Number(data.peak_equity ?? data.peakEquity ?? 0),
  };
};

const mapTrade = (data: any): ForexTrade => {
  return {
    id: Number(data.id),
    symbol: String(data.symbol ?? '').toUpperCase(),
    side: String(data.side ?? 'BUY').toUpperCase() === 'SELL' ? 'SELL' : 'BUY',
    lots: Number(data.lots ?? 0),
    openTime: String(data.open_time),
    closeTime: data.close_time != null ? String(data.close_time) : null,
    openPrice: Number(data.open_price ?? 0),
    closePrice: data.close_price != null ? Number(data.close_price) : null,
    sl: data.sl != null ? Number(data.sl) : undefined,
    tp: data.tp != null ? Number(data.tp) : undefined,
    commission: Number(data.commission ?? 0),
    swap: Number(data.swap ?? 0),
    profit: data.profit != null ? Number(data.profit) : null,
    notes: data.notes != null ? String(data.notes) : null,
    status: String(data.status) === 'closed' ? 'closed' : 'open',
  };
};

export function ForexProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<ForexAccount>({
    currency: 'USD',
    leverage: 100,
    initialBalance: 10000,
    initialDate: null,
    balance: 10000,
    equity: 10000,
    margin: 0,
    freeMargin: 10000,
    marginLevel: 0,
    maxDrawdown: 0,
    peakEquity: 10000,
  });

  const [openTrades, setOpenTrades] = useState<ForexTrade[]>([]);
  const [closedTrades, setClosedTrades] = useState<ForexTrade[]>([]);
  const [capitalHistory, setCapitalHistory] = useState<ForexCapitalPoint[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = async () => {
    const [accountRes, positionsRes, tradesRes, capitalRes] = await Promise.all([
      axios.get('/api/forex/account'),
      axios.get('/api/forex/positions'),
      axios.get('/api/forex/trades', { params: { page: 1, page_size: 500 } }),
      axios.get('/api/forex/capital-history'),
    ]);

    setAccount(mapAccount(accountRes.data));
    setOpenTrades((positionsRes.data ?? []).map(mapTrade));

    const items = tradesRes.data?.items ?? [];
    const closed = items.filter((t: any) => String(t.status) === 'closed' && t.close_time);
    setClosedTrades(closed.map(mapTrade));

    setCapitalHistory(
      (capitalRes.data ?? []).map((p: any) => ({
        date: String(p.date),
        equity: Number(p.equity ?? 0),
        balance: Number(p.balance ?? 0),
      }))
    );
  };

  useEffect(() => {
    refresh().catch(() => {});
  }, []);

  const createTrade = async (payload: ForexTradeCreatePayload) => {
    await axios.post('/api/forex/trades', payload);
    await refresh();
    setRefreshKey((v) => v + 1);
  };

  const closeTrade = async (tradeId: number, payload: ForexTradeClosePayload) => {
    await axios.post(`/api/forex/trades/${tradeId}/close`, payload);
    await refresh();
    setRefreshKey((v) => v + 1);
  };

  const updateTrade = async (tradeId: number, payload: ForexTradeUpdatePayload) => {
    await axios.patch(`/api/forex/trades/${tradeId}`, payload);
    await refresh();
    setRefreshKey((v) => v + 1);
  };

  const deleteTrade = async (tradeId: number) => {
    await axios.delete(`/api/forex/trades/${tradeId}`);
    await refresh();
    setRefreshKey((v) => v + 1);
  };

  const clearAllTrades = async () => {
    const res = await axios.delete('/api/forex/trades/clear-all');
    await refresh();
    setRefreshKey((v) => v + 1);
    return { deleted_count: Number(res.data?.deleted_count ?? 0) };
  };

  const updateAccount = async (payload: ForexAccountUpdatePayload) => {
    const res = await axios.patch('/api/forex/account', payload);
    setAccount(mapAccount(res.data));
    await refresh();
  };

  const setInitialCapital = async (payload: ForexInitialCapitalPayload) => {
    await axios.post('/api/forex/account/initial', payload);
    await refresh();
    setRefreshKey((v) => v + 1);
  };

  const resetAccount = async (payload: ForexAccountResetPayload) => {
    await axios.post('/api/forex/account/reset', payload);
    setOpenTrades([]);
    setClosedTrades([]);
    setCapitalHistory([]);
    await refresh();
    setRefreshKey((v) => v + 1);
  };

  const fetchQuotes = async (symbols: string[]) => {
    const list = (symbols ?? []).map((s) => String(s ?? '').trim()).filter(Boolean);
    if (list.length === 0) return [];
    const res = await axios.get('/api/forex/quotes', { params: { symbols: list.join(',') } });
    return (res.data ?? []).map((q: any) => ({
      symbol: String(q.symbol ?? '').toUpperCase(),
      price: q.price != null ? Number(q.price) : null,
      bid: q.bid != null ? Number(q.bid) : null,
      ask: q.ask != null ? Number(q.ask) : null,
      asof: String(q.asof ?? ''),
      source: String(q.source ?? ''),
      error: q.error != null ? String(q.error) : null,
    })) as ForexQuote[];
  };

  const value = useMemo<ForexContextType>(() => {
    return {
      account,
      openTrades,
      closedTrades,
      capitalHistory,
      refreshKey,
      createTrade,
      closeTrade,
      updateTrade,
      deleteTrade,
      clearAllTrades,
      updateAccount,
      setInitialCapital,
      resetAccount,
      fetchQuotes,
      refresh,
    };
  }, [account, openTrades, closedTrades, capitalHistory, refreshKey]);

  return <ForexContext.Provider value={value}>{children}</ForexContext.Provider>;
}

export const useForex = () => {
  const context = useContext(ForexContext);
  if (context === undefined) throw new Error('useForex must be used within a ForexProvider');
  return context;
};
