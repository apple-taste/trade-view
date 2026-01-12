import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

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
}

const TradeContext = createContext<TradeContextType | undefined>(undefined);

export function TradeProvider({ children }: { children: ReactNode }) {
  const [calendarRefreshKey, setCalendarRefreshKey] = useState(0);
  const [positionsRefreshKey, setPositionsRefreshKey] = useState(0);
  const [analysisRefreshKey, setAnalysisRefreshKey] = useState(0);
  const [userPanelRefreshKey, setUserPanelRefreshKey] = useState(0);
  const [tradeHistoryRefreshKey, setTradeHistoryRefreshKey] = useState(0);

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
