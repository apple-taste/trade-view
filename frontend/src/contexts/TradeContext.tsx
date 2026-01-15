import { createContext, useContext, useState, useCallback, ReactNode, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useAuth } from './AuthContext';

type Strategy = {
  id: number;
  name: string;
  market: string;
  uid: string;
  initial_capital?: number | null;
  initial_date?: string | null;
};

interface TradeContextType {
  refreshCalendar: () => void;
  refreshPositions: () => void;
  refreshAnalysis: () => void;
  refreshUserPanel: () => void;
  refreshTradeHistory: () => void;
  refreshAll: () => void;
  _calendarRefreshKey: number;
  _positionsRefreshKey: number;
  _analysisRefreshKey: number;
  _userPanelRefreshKey: number;
  _tradeHistoryRefreshKey: number;
  lastAddedTrade: any | null;
  setLastAddedTrade: (trade: any | null) => void;
  lastUpdatedTrade: any | null;
  setLastUpdatedTrade: (trade: any | null) => void;
  lastDeletedTradeId: number | null;
  setLastDeletedTradeId: (id: number | null) => void;

  strategies: Strategy[];
  currentStrategyId: number | null;
  effectiveStrategyId: number | null;
  setCurrentStrategyId: (strategyId: number | null) => void;
  refreshStrategies: () => Promise<void>;
  createStrategy: (name: string) => Promise<Strategy | null>;
  deleteStrategy: (strategyId: number) => Promise<void>;
  deleteAllStrategies: () => Promise<void>;

  forexStrategies: Strategy[];
  currentForexStrategyId: number | null;
  effectiveForexStrategyId: number | null;
  setCurrentForexStrategyId: (strategyId: number | null) => void;
  refreshForexStrategies: () => Promise<void>;
  createForexStrategy: (name: string) => Promise<Strategy | null>;
  deleteForexStrategy: (strategyId: number) => Promise<void>;
  deleteAllForexStrategies: () => Promise<void>;
}

const TradeContext = createContext<TradeContextType | undefined>(undefined);

export function TradeProvider({ children }: { children: ReactNode }) {
  const { token, loading } = useAuth();
  const [calendarRefreshKey, setCalendarRefreshKey] = useState(0);
  const [positionsRefreshKey, setPositionsRefreshKey] = useState(0);
  const [analysisRefreshKey, setAnalysisRefreshKey] = useState(0);
  const [userPanelRefreshKey, setUserPanelRefreshKey] = useState(0);
  const [tradeHistoryRefreshKey, setTradeHistoryRefreshKey] = useState(0);
  const [lastAddedTrade, setLastAddedTrade] = useState<any | null>(null);
  const [lastUpdatedTrade, setLastUpdatedTrade] = useState<any | null>(null);
  const [lastDeletedTradeId, setLastDeletedTradeId] = useState<number | null>(null);

  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [currentStrategyId, setCurrentStrategyIdState] = useState<number | null>(() => {
    const raw = localStorage.getItem('currentStockStrategyId');
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  });

  const [forexStrategies, setForexStrategies] = useState<Strategy[]>([]);
  const [currentForexStrategyId, setCurrentForexStrategyIdState] = useState<number | null>(() => {
    const raw = localStorage.getItem('currentForexStrategyId');
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  });

  const refreshCalendar = useCallback(() => {
    setCalendarRefreshKey(prev => prev + 1);
  }, []);

  const refreshPositions = useCallback(() => {
    setPositionsRefreshKey(prev => prev + 1);
  }, []);

  const refreshAnalysis = useCallback(() => {
    setAnalysisRefreshKey(prev => prev + 1);
  }, []);

  const refreshUserPanel = useCallback(() => {
    setUserPanelRefreshKey(prev => prev + 1);
  }, []);

  const refreshTradeHistory = useCallback(() => {
    setTradeHistoryRefreshKey(prev => prev + 1);
  }, []);

  const refreshAll = useCallback(() => {
    refreshCalendar();
    refreshPositions();
    refreshAnalysis();
    refreshUserPanel();
    refreshTradeHistory();
  }, [refreshCalendar, refreshPositions, refreshAnalysis, refreshUserPanel, refreshTradeHistory]);

  const effectiveStrategyId = useMemo(() => {
    return currentStrategyId;
  }, [currentStrategyId, strategies]);

  const effectiveForexStrategyId = useMemo(() => {
    return currentForexStrategyId;
  }, [currentForexStrategyId, forexStrategies]);

  const refreshStrategies = useCallback(async () => {
    const res = await axios.get('/api/user/strategies', { params: { market: 'stock' } });
    const rawList = (res.data ?? []) as Strategy[];
    const list = rawList.filter((s) => s?.name !== '默认策略');
    setStrategies(list);

    if (list.length === 0) {
      setCurrentStrategyIdState(null);
      localStorage.removeItem('currentStockStrategyId');
      return;
    }

    const stored = localStorage.getItem('currentStockStrategyId');
    const storedId = stored != null ? Number(stored) : null;
    const exists = storedId != null && list.some((s) => s.id === storedId);
    if (exists) {
      setCurrentStrategyIdState(storedId);
      return;
    }

    setCurrentStrategyIdState(null);
    localStorage.removeItem('currentStockStrategyId');
  }, []);

  const refreshForexStrategies = useCallback(async () => {
    const res = await axios.get('/api/user/strategies', { params: { market: 'forex' } });
    const list = (res.data ?? []) as Strategy[];
    setForexStrategies(list);

    if (list.length === 0) {
      setCurrentForexStrategyIdState(null);
      localStorage.removeItem('currentForexStrategyId');
      return;
    }

    const stored = localStorage.getItem('currentForexStrategyId');
    const storedId = stored != null ? Number(stored) : null;
    const exists = storedId != null && list.some((s) => s.id === storedId);
    if (exists) {
      setCurrentForexStrategyIdState(storedId);
      return;
    }

    setCurrentForexStrategyIdState(null);
    localStorage.removeItem('currentForexStrategyId');
  }, []);

  const setCurrentStrategyId = useCallback(
    (strategyId: number | null) => {
      setCurrentStrategyIdState(strategyId);
      if (strategyId == null) {
        localStorage.removeItem('currentStockStrategyId');
      } else {
        localStorage.setItem('currentStockStrategyId', String(strategyId));
      }
      refreshAll();
    },
    [refreshAll]
  );

  const setCurrentForexStrategyId = useCallback(
    (strategyId: number | null) => {
      setCurrentForexStrategyIdState(strategyId);
      if (strategyId == null) {
        localStorage.removeItem('currentForexStrategyId');
      } else {
        localStorage.setItem('currentForexStrategyId', String(strategyId));
      }
      refreshAll();
    },
    [refreshAll]
  );

  const createStrategy = useCallback(
    async (name: string) => {
      const trimmed = String(name ?? '').trim();
      if (!trimmed) return null;
      const res = await axios.post('/api/user/strategies', { name: trimmed }, { params: { market: 'stock' } });
      const created = res.data as Strategy;
      await refreshStrategies();
      if (created?.id != null) {
        setCurrentStrategyId(created.id);
      }
      return created;
    },
    [refreshStrategies, setCurrentStrategyId]
  );

  const createForexStrategy = useCallback(
    async (name: string) => {
      const trimmed = String(name ?? '').trim();
      if (!trimmed) return null;
      const res = await axios.post('/api/user/strategies', { name: trimmed }, { params: { market: 'forex' } });
      const created = res.data as Strategy;
      await refreshForexStrategies();
      if (created?.id != null) {
        setCurrentForexStrategyId(created.id);
      }
      return created;
    },
    [refreshForexStrategies, setCurrentForexStrategyId]
  );

  const deleteStrategy = useCallback(
    async (strategyId: number) => {
      const nextId = strategies.filter((s) => s.id !== strategyId)[0]?.id ?? null;
      await axios.delete(`/api/user/strategies/${strategyId}`, { params: { market: 'stock' } });
      await refreshStrategies();
      setCurrentStrategyIdState((prev) => {
        if (prev !== strategyId) return prev;
        if (nextId == null) {
          localStorage.removeItem('currentStockStrategyId');
        } else {
          localStorage.setItem('currentStockStrategyId', String(nextId));
        }
        return nextId;
      });
      refreshAll();
    },
    [refreshAll, refreshStrategies, strategies]
  );

  const deleteForexStrategy = useCallback(
    async (strategyId: number) => {
      const nextId = forexStrategies.filter((s) => s.id !== strategyId)[0]?.id ?? null;
      await axios.delete(`/api/user/strategies/${strategyId}`, { params: { market: 'forex' } });
      await refreshForexStrategies();
      setCurrentForexStrategyIdState((prev) => {
        if (prev !== strategyId) return prev;
        if (nextId == null) {
          localStorage.removeItem('currentForexStrategyId');
        } else {
          localStorage.setItem('currentForexStrategyId', String(nextId));
        }
        return nextId;
      });
      refreshAll();
    },
    [forexStrategies, refreshAll, refreshForexStrategies]
  );

  const deleteAllStrategies = useCallback(async () => {
    await axios.delete('/api/user/strategies', { params: { market: 'stock' } });
    await refreshStrategies();
    setCurrentStrategyIdState(null);
    localStorage.removeItem('currentStockStrategyId');
    refreshAll();
  }, [refreshAll, refreshStrategies]);

  const deleteAllForexStrategies = useCallback(async () => {
    await axios.delete('/api/user/strategies', { params: { market: 'forex' } });
    await refreshForexStrategies();
    setCurrentForexStrategyIdState(null);
    localStorage.removeItem('currentForexStrategyId');
    refreshAll();
  }, [refreshAll, refreshForexStrategies]);

  useEffect(() => {
    if (loading) return;
    if (!token) {
      setStrategies([]);
      setCurrentStrategyIdState(null);
      localStorage.removeItem('currentStockStrategyId');
      return;
    }
    refreshStrategies().catch(() => {});
  }, [loading, refreshStrategies, token]);

  useEffect(() => {
    if (loading) return;
    if (!token) {
      setForexStrategies([]);
      setCurrentForexStrategyIdState(null);
      localStorage.removeItem('currentForexStrategyId');
      return;
    }
    refreshForexStrategies().catch(() => {});
  }, [loading, refreshForexStrategies, token]);

  return (
    <TradeContext.Provider
      value={{
        refreshCalendar,
        refreshPositions,
        refreshAnalysis,
        refreshUserPanel,
        refreshTradeHistory,
        refreshAll,
        _calendarRefreshKey: calendarRefreshKey,
        _positionsRefreshKey: positionsRefreshKey,
        _analysisRefreshKey: analysisRefreshKey,
        _userPanelRefreshKey: userPanelRefreshKey,
        _tradeHistoryRefreshKey: tradeHistoryRefreshKey,
        lastAddedTrade,
        setLastAddedTrade,
        lastUpdatedTrade,
        setLastUpdatedTrade,
        lastDeletedTradeId,
        setLastDeletedTradeId,

        strategies,
        currentStrategyId,
        effectiveStrategyId,
        setCurrentStrategyId,
        refreshStrategies,
        createStrategy,
        deleteStrategy,
        deleteAllStrategies,

        forexStrategies,
        currentForexStrategyId,
        effectiveForexStrategyId,
        setCurrentForexStrategyId,
        refreshForexStrategies,
        createForexStrategy,
        deleteForexStrategy,
        deleteAllForexStrategies,
      }}
    >
      {children}
    </TradeContext.Provider>
  );
}

export function useTrade() {
  const context = useContext(TradeContext);
  if (context === undefined) {
    throw new Error('useTrade must be used within a TradeProvider');
  }
  return context;
}
