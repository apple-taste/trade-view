import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from 'react';

type Language = 'zh' | 'en';

type LocaleContextType = {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: string) => string;
};

const LocaleContext = createContext<LocaleContextType | undefined>(undefined);

const translations: Record<Language, Record<string, string>> = {
  zh: {
    'app.title': 'JOJOLAND 交易系统',
    'nav.welcome': '欢迎',
    'nav.logout': '退出',
    'nav.resetLayout': '重置布局',
    'nav.switchToStock': 'A股交易',
    'nav.switchToForex': '外汇交易',
    'nav.confirmResetLayout': '确定要恢复默认布局吗？',
    'lang.zh': '中文',
    'lang.en': 'English',
    'forex.title': '外汇交易账单',
    'forex.balance': '余额',
    'forex.equity': '净值',
    'forex.settings': '交易参数',
    'forex.marketWatch': '行情',
    'forex.order': '下单',
    'forex.terminal': '交易终端',
    'forex.tab.positions': '持仓',
    'forex.tab.pending': '挂单',
    'forex.tab.history': '历史',
    'forex.totalProfit': '总盈亏',
    'forex.noPending': '暂无挂单',
    'forex.noHistory': '暂无历史记录',
    'forex.noData': '暂无数据',
    'forex.margin': '保证金',
    'forex.freeMargin': '可用保证金',
    'forex.marginLevel': '保证金水平',
    'forex.stopOutWarning': '强平风险警告',
    'forex.maxDrawdown': '最大回撤',
    'forex.selectSymbol': '请选择品种',
    'forex.marketExecution': '市价单',
    'forex.pendingOrder': '挂单',
    'forex.volumeLots': '手数 (Lots)',
    'forex.max': '最大',
    'forex.stopLoss': '止损',
    'forex.takeProfit': '止盈',
    'forex.type': '类型',
    'forex.price': '价格',
    'forex.placeOrder': '提交挂单',
    'forex.sellByMarket': '市价卖出',
    'forex.buyByMarket': '市价买入',
    'forex.spread': '点差',
    'forex.accountCurrency': '账户币种',
    'forex.leverage': '杠杆',
    'forex.generalSettings': '通用设置',
    'forex.brokerName': '经纪商名称',
    'forex.initialBalance': '初始资金',
    'forex.initialDate': '起始日期',
    'forex.setInitialCapital': '设置资金锚点',
    'forex.addTrade': '新增交易',
    'forex.closeTrade': '平仓',
    'forex.editTrade': '编辑',
    'forex.deleteTrade': '删除',
    'forex.clearAllTrades': '清空记录',
    'forex.feesSwaps': '费用与隔夜利息',
    'forex.commissionPerLot': '手续费（$/Lot）',
    'forex.swapLong': '多单隔夜（点）',
    'forex.swapShort': '空单隔夜（点）',
    'forex.spreads': '点差（Pips）',
    'forex.confirmResetAccount': '确定要重置账户吗？将清空所有持仓与历史。',
    'forex.resetAccount': '重置账户',
    'forex.save': '保存',
    'forex.close': '关闭',
    'forex.cancel': '取消',
    'forex.brokerSettings': '经纪商设置',
  },
  en: {
    'app.title': 'JOJOLAND Trading System',
    'nav.welcome': 'Welcome',
    'nav.logout': 'Logout',
    'nav.resetLayout': 'Reset layout',
    'nav.switchToStock': 'A-Share',
    'nav.switchToForex': 'Forex',
    'nav.confirmResetLayout': 'Reset to default layout?',
    'lang.zh': '中文',
    'lang.en': 'English',
    'forex.title': 'Forex Ledger',
    'forex.balance': 'Balance',
    'forex.equity': 'Equity',
    'forex.settings': 'Settings',
    'forex.marketWatch': 'Market Watch',
    'forex.order': 'Order',
    'forex.terminal': 'Terminal',
    'forex.tab.positions': 'Positions',
    'forex.tab.pending': 'Pending',
    'forex.tab.history': 'History',
    'forex.totalProfit': 'Total P/L',
    'forex.noPending': 'No pending orders',
    'forex.noHistory': 'No trade history',
    'forex.noData': 'No data',
    'forex.margin': 'Margin',
    'forex.freeMargin': 'Free Margin',
    'forex.marginLevel': 'Margin Level',
    'forex.stopOutWarning': 'STOP OUT WARNING',
    'forex.maxDrawdown': 'Max DD',
    'forex.selectSymbol': 'Select a symbol',
    'forex.marketExecution': 'Market Execution',
    'forex.pendingOrder': 'Pending Order',
    'forex.volumeLots': 'Volume (Lots)',
    'forex.max': 'Max',
    'forex.stopLoss': 'Stop Loss',
    'forex.takeProfit': 'Take Profit',
    'forex.type': 'Type',
    'forex.price': 'Price',
    'forex.placeOrder': 'Place Order',
    'forex.sellByMarket': 'Sell by Market',
    'forex.buyByMarket': 'Buy by Market',
    'forex.spread': 'Spread',
    'forex.accountCurrency': 'Account Currency',
    'forex.leverage': 'Leverage',
    'forex.generalSettings': 'General Settings',
    'forex.brokerName': 'Broker Name',
    'forex.initialBalance': 'Initial Balance',
    'forex.initialDate': 'Start Date',
    'forex.setInitialCapital': 'Set Capital Anchor',
    'forex.addTrade': 'Add Trade',
    'forex.closeTrade': 'Close',
    'forex.editTrade': 'Edit',
    'forex.deleteTrade': 'Delete',
    'forex.clearAllTrades': 'Clear All',
    'forex.feesSwaps': 'Fees & Swaps',
    'forex.commissionPerLot': 'Commission ($/Lot)',
    'forex.swapLong': 'Swap Long (Points)',
    'forex.swapShort': 'Swap Short (Points)',
    'forex.spreads': 'Spreads (Pips)',
    'forex.confirmResetAccount': 'Reset account? All positions and history will be cleared.',
    'forex.resetAccount': 'Reset Account',
    'forex.save': 'Save',
    'forex.close': 'Close',
    'forex.cancel': 'Cancel',
    'forex.brokerSettings': 'Broker Settings',
  },
};

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>('zh');

  useEffect(() => {
    const saved = localStorage.getItem('app_language');
    if (saved === 'zh' || saved === 'en') setLanguageState(saved);
  }, []);

  const setLanguage = (next: Language) => {
    setLanguageState(next);
    localStorage.setItem('app_language', next);
  };

  const t = useMemo(() => {
    return (key: string) => translations[language][key] ?? translations.zh[key] ?? key;
  }, [language]);

  return (
    <LocaleContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale() {
  const context = useContext(LocaleContext);
  if (!context) throw new Error('useLocale must be used within a LocaleProvider');
  return context;
}
