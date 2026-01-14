import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { Brain, TrendingUp, TrendingDown, Target, DollarSign, Clock, BarChart3, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import { useTrade } from '../../contexts/TradeContext';

const EMPTY_ANALYSIS: AnalysisData = {
  summary: {
    totalTrades: 0,
    winRate: 0,
    totalProfit: 0,
    averageHoldingDays: 0,
    stopLossExecuted: 0,
    takeProfitExecuted: 0,
    profitLossRatio: 0,
  },
};

interface AnalysisData {
  summary: {
    totalTrades: number;
    winRate: number;
    totalProfit: number;
    averageHoldingDays: number;
    stopLossExecuted: number;
    takeProfitExecuted: number;
    profitLossRatio: number;
  };
  detailed_analysis?: {
    stop_loss_analysis: string;
    take_profit_analysis: string;
    entry_price_analysis: string;
    profit_loss_ratio_analysis: string;
    capital_management: string;
    key_insights: string[];
    recommendations: string[];
  };
}

interface AnalysisPanelProps {
  isMinimized?: boolean;
  onToggleMinimize?: () => void;
  systemMode?: 'stock' | 'forex';
  refreshKey?: number;
}

export default function AnalysisPanel({ isMinimized = false, onToggleMinimize, systemMode = 'stock', refreshKey }: AnalysisPanelProps) {
  const [analysis, setAnalysis] = useState<AnalysisData>(EMPTY_ANALYSIS);
  const [loading, setLoading] = useState(true); // 初始为true，自动加载统计摘要
  const [aiLoading, setAiLoading] = useState(false);
  const { _analysisRefreshKey } = useTrade();

  // 获取统计摘要（本地计算，不调用AI）
  const fetchSummary = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/analysis/trade-summary', {
        params: { use_ai: false, system_mode: systemMode },
      });
      setAnalysis(response.data);
    } catch (error) {
      console.error('获取统计摘要失败:', error);
      setAnalysis(EMPTY_ANALYSIS);
    } finally {
      setLoading(false);
    }
  }, [systemMode]);

  // 自动获取统计摘要（本地计算，不调用AI）
  useEffect(() => {
    fetchSummary();
  }, [_analysisRefreshKey, refreshKey, fetchSummary]); // 当刷新键变化时重新获取

  // 获取AI分析（调用AI，传入开仓历史和资金曲线）
  const fetchAiAnalysis = async () => {
    setAiLoading(true);
    try {
      const response = await axios.get('/api/analysis/trade-summary', {
        params: { use_ai: true, system_mode: systemMode },
      });
      setAnalysis(response.data);
    } catch (error) {
      console.error('获取AI分析失败:', error);
      alert('AI分析失败，请稍后重试');
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className={`jojo-card jojo-card-no-scale p-4 ${isMinimized ? 'h-full flex flex-col justify-center' : ''}`}>
      {/* 标题区域 */}
      <div className={`flex items-center justify-between ${isMinimized ? '' : 'mb-4 pb-3 border-b border-jojo-gold/30'}`}>
        <div className="flex items-center space-x-2">
          <div className="p-2 bg-gradient-to-br from-jojo-gold to-jojo-gold-dark rounded-lg">
            <Brain className="text-jojo-blue" size={20} />
          </div>
          <h2 className="jojo-title text-xl">AI 交易分析</h2>
        </div>
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1 text-xs text-gray-400">
            <Sparkles size={12} />
            <span className="hidden sm:inline">智能分析</span>
          </div>
          {onToggleMinimize && (
            <button
              onClick={onToggleMinimize}
              className="p-1 hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-white"
              title={isMinimized ? "展开面板" : "最小化面板"}
            >
              {isMinimized ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>
          )}
        </div>
      </div>

      {!isMinimized && (
        <>
          {loading ? (
            <div className="py-10 text-center">
              <div className="text-jojo-gold animate-jojo-pulse">加载统计摘要中...</div>
            </div>
          ) : (
            <>
              {/* 统计摘要（本地计算） */}
              <div className="mb-4">
                <div className="flex items-center space-x-2 mb-3">
                  <BarChart3 className="text-jojo-gold" size={16} />
                  <h3 className="text-sm font-semibold text-jojo-gold">📊 交易统计摘要</h3>
                </div>
                
                {/* 主要指标 - 4个核心指标 */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                  <div className="relative p-3 bg-gradient-to-br from-jojo-blue-light to-jojo-blue rounded-lg border-2 border-jojo-gold/50 hover:border-jojo-gold transition-all group">
                    <div className="absolute top-2 right-2 opacity-20">
                      <Target className="text-jojo-gold" size={24} />
                    </div>
                    <div className="flex items-center space-x-2 mb-1">
                      <Target className="text-jojo-gold" size={14} />
                      <p className="text-xs text-gray-400 font-medium">总交易次数</p>
                    </div>
                    <p className="text-2xl font-bold text-jojo-gold mt-1">{analysis.summary.totalTrades}</p>
                    <div className="mt-1 h-1 bg-jojo-gold/20 rounded-full overflow-hidden">
                      <div className="h-full bg-jojo-gold rounded-full" style={{ width: `${Math.min(analysis.summary.totalTrades * 10, 100)}%` }}></div>
                    </div>
                  </div>
                  
                  <div className={`relative p-3 rounded-lg border-2 transition-all group ${
                    analysis.summary.winRate >= 50 
                      ? 'bg-gradient-to-br from-green-500/20 to-green-600/10 border-green-400/70 hover:border-green-400' 
                      : 'bg-gradient-to-br from-red-500/20 to-red-600/10 border-red-400/70 hover:border-red-400'
                  }`}>
                    <div className="absolute top-2 right-2 opacity-20">
                      <TrendingUp className={analysis.summary.winRate >= 50 ? 'text-green-400' : 'text-red-400'} size={24} />
                    </div>
                    <div className="flex items-center space-x-2 mb-1">
                      <TrendingUp className={analysis.summary.winRate >= 50 ? 'text-green-400' : 'text-red-400'} size={14} />
                      <p className="text-xs text-gray-400 font-medium">胜率</p>
                    </div>
                    <p className={`text-2xl font-bold mt-1 ${analysis.summary.winRate >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                      {analysis.summary.winRate.toFixed(1)}%
                    </p>
                    <div className="mt-1 h-1 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${analysis.summary.winRate >= 50 ? 'bg-green-400' : 'bg-red-400'}`} 
                        style={{ width: `${analysis.summary.winRate}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className={`relative p-3 rounded-lg border-2 transition-all group ${
                    analysis.summary.totalProfit >= 0 
                      ? 'bg-gradient-to-br from-green-500/20 to-green-600/10 border-green-400/70 hover:border-green-400' 
                      : 'bg-gradient-to-br from-red-500/20 to-red-600/10 border-red-400/70 hover:border-red-400'
                  }`}>
                    <div className="absolute top-2 right-2 opacity-20">
                      <DollarSign className={analysis.summary.totalProfit >= 0 ? 'text-green-400' : 'text-red-400'} size={24} />
                    </div>
                    <div className="flex items-center space-x-2 mb-1">
                      <DollarSign className={analysis.summary.totalProfit >= 0 ? 'text-green-400' : 'text-red-400'} size={14} />
                      <p className="text-xs text-gray-400 font-medium">累计盈亏</p>
                    </div>
                    <p className={`text-xl font-bold mt-1 ${analysis.summary.totalProfit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {analysis.summary.totalProfit >= 0 ? '+' : ''}{analysis.summary.totalProfit.toFixed(2)}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">元</p>
                  </div>
                  
                  <div className="relative p-3 bg-gradient-to-br from-jojo-blue-light to-purple-900/20 rounded-lg border-2 border-purple-400/50 hover:border-purple-400 transition-all group">
                    <div className="absolute top-2 right-2 opacity-20">
                      <Clock className="text-purple-400" size={24} />
                    </div>
                    <div className="flex items-center space-x-2 mb-1">
                      <Clock className="text-purple-400" size={14} />
                      <p className="text-xs text-gray-400 font-medium">平均持仓</p>
                    </div>
                    <p className="text-xl font-bold text-purple-400 mt-1">{analysis.summary.averageHoldingDays.toFixed(1)}</p>
                    <p className="text-xs text-gray-500 mt-0.5">天</p>
                  </div>
                </div>
                
                {/* 次要指标 - 3个执行指标 */}
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-2.5 bg-gradient-to-br from-blue-500/15 to-blue-600/5 rounded-lg border border-blue-400/50 hover:border-blue-400 transition-all">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-xs text-gray-400">止损执行</p>
                      <TrendingDown className="text-blue-400" size={12} />
                    </div>
                    <p className="text-lg font-bold text-blue-400">{analysis.summary.stopLossExecuted}</p>
                    <p className="text-xs text-gray-500">次</p>
                  </div>
                  <div className="p-2.5 bg-gradient-to-br from-green-500/15 to-green-600/5 rounded-lg border border-green-400/50 hover:border-green-400 transition-all">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-xs text-gray-400">止盈执行</p>
                      <TrendingUp className="text-green-400" size={12} />
                    </div>
                    <p className="text-lg font-bold text-green-400">{analysis.summary.takeProfitExecuted}</p>
                    <p className="text-xs text-gray-500">次</p>
                  </div>
                  <div className="p-2.5 bg-gradient-to-br from-yellow-500/15 to-yellow-600/5 rounded-lg border border-yellow-400/50 hover:border-yellow-400 transition-all">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-xs text-gray-400">盈亏比</p>
                      <BarChart3 className="text-yellow-400" size={12} />
                    </div>
                    <p className="text-lg font-bold text-yellow-400">{analysis.summary.profitLossRatio.toFixed(2)}</p>
                    <p className="text-xs text-gray-500">比率</p>
                  </div>
                </div>
              </div>

              {/* AI详细分析 */}
              {aiLoading ? (
                <div className="mt-4 pt-4 border-t border-jojo-gold/30">
                  <div className="flex flex-col items-center justify-center py-8">
                    <div className="relative">
                      <Brain className="text-jojo-gold animate-pulse" size={32} />
                      <div className="absolute inset-0 bg-jojo-gold/20 rounded-full animate-ping"></div>
                    </div>
                    <p className="text-jojo-gold mt-4 text-sm font-medium">AI正在深度分析中...</p>
                    <p className="text-gray-400 text-xs mt-1">请稍候，正在分析交易历史和资金曲线</p>
                  </div>
                </div>
              ) : analysis.detailed_analysis ? (
                <div className="mt-4 pt-4 border-t border-jojo-gold/30">
                  <div className="flex items-center space-x-2 mb-3">
                    <div className="p-1.5 bg-gradient-to-br from-purple-500 to-purple-700 rounded-lg">
                      <Sparkles className="text-white" size={14} />
                    </div>
                    <h3 className="text-sm font-semibold text-jojo-purple">🤖 AI深度分析报告</h3>
                  </div>
                  
                  <div className="space-y-3 pr-2 custom-scrollbar">
            {/* 止损止盈分析 */}
            <div className="p-3 bg-gradient-to-r from-red-500/10 to-transparent rounded-lg border-l-4 border-red-400">
                      <div className="flex items-center space-x-2 mb-2">
                        <TrendingDown className="text-red-400" size={14} />
                        <h4 className="text-xs font-semibold text-red-400">止损止盈分析</h4>
                      </div>
                      <p className="text-gray-300 text-xs leading-relaxed pl-5">
                        {analysis.detailed_analysis.stop_loss_analysis.substring(0, 150)}
                        {analysis.detailed_analysis.stop_loss_analysis.length > 150 && '...'}
                      </p>
                    </div>
                    
                    {/* 入场价格分析 */}
                    <div className="p-3 bg-gradient-to-r from-blue-500/10 to-transparent rounded-lg border-l-4 border-blue-400">
                      <div className="flex items-center space-x-2 mb-2">
                        <Target className="text-blue-400" size={14} />
                        <h4 className="text-xs font-semibold text-blue-400">入场价格分析</h4>
                      </div>
                      <p className="text-gray-300 text-xs leading-relaxed pl-5">
                        {analysis.detailed_analysis.entry_price_analysis.substring(0, 150)}
                        {analysis.detailed_analysis.entry_price_analysis.length > 150 && '...'}
                      </p>
                    </div>
                    
                    {/* 盈亏比分析 */}
                    <div className="p-3 bg-gradient-to-r from-yellow-500/10 to-transparent rounded-lg border-l-4 border-yellow-400">
                      <div className="flex items-center space-x-2 mb-2">
                        <BarChart3 className="text-yellow-400" size={14} />
                        <h4 className="text-xs font-semibold text-yellow-400">盈亏比分析</h4>
                      </div>
                      <p className="text-gray-300 text-xs leading-relaxed pl-5">
                        {analysis.detailed_analysis.profit_loss_ratio_analysis.substring(0, 150)}
                        {analysis.detailed_analysis.profit_loss_ratio_analysis.length > 150 && '...'}
                      </p>
                    </div>
                    
                    {/* 资金管理建议 */}
                    <div className="p-3 bg-gradient-to-r from-green-500/10 to-transparent rounded-lg border-l-4 border-green-400">
                      <div className="flex items-center space-x-2 mb-2">
                        <DollarSign className="text-green-400" size={14} />
                        <h4 className="text-xs font-semibold text-green-400">资金管理建议</h4>
                      </div>
                      <p className="text-gray-300 text-xs leading-relaxed pl-5">
                        {analysis.detailed_analysis.capital_management.substring(0, 150)}
                        {analysis.detailed_analysis.capital_management.length > 150 && '...'}
                      </p>
                    </div>
                    
                    {/* 关键洞察 */}
                    {analysis.detailed_analysis.key_insights && analysis.detailed_analysis.key_insights.length > 0 && (
                      <div className="p-3 bg-gradient-to-r from-purple-500/10 to-transparent rounded-lg border-l-4 border-purple-400">
                        <div className="flex items-center space-x-2 mb-2">
                          <Sparkles className="text-purple-400" size={14} />
                          <h4 className="text-xs font-semibold text-purple-400">关键洞察</h4>
                        </div>
                        <ul className="space-y-1.5 pl-5">
                          {analysis.detailed_analysis.key_insights.slice(0, 3).map((insight, index) => (
                            <li key={index} className="text-gray-300 text-xs leading-relaxed flex items-start">
                              <span className="text-purple-400 mr-2">•</span>
                              <span>{insight}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="mt-4 pt-4 border-t border-jojo-gold/30">
                  <div className="text-center py-6">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-purple-500/20 to-purple-700/20 mb-3">
                      <Brain className="text-purple-400" size={24} />
                    </div>
                    <p className="text-gray-300 mb-1 text-sm font-medium">AI深度分析</p>
                    <p className="text-gray-500 mb-4 text-xs">点击下方按钮获取专业的交易分析和优化建议</p>
                    <button
                      onClick={fetchAiAnalysis}
                      className="jojo-button flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-purple-800 hover:from-purple-700 hover:to-purple-900 text-sm px-4 py-2 mx-auto"
                    >
                      <Brain size={16} />
                      <span>🤖 获取AI深度分析</span>
                    </button>
                  </div>
                </div>
              )}

              {/* 操作按钮 */}
              <div className="mt-4 pt-3 border-t border-jojo-gold/20 flex space-x-2">
                <button
                  onClick={fetchSummary}
                  className="flex-1 jojo-button text-xs py-2"
                >
                  🔄 刷新统计
                </button>
                {analysis.detailed_analysis && (
                  <button
                    onClick={fetchAiAnalysis}
                    className="flex-1 px-3 py-2 text-xs font-semibold text-white rounded-lg bg-gradient-to-r from-purple-600 to-purple-800 hover:from-purple-700 hover:to-purple-900 transition-all"
                  >
                    🔄 重新分析
                  </button>
                )}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
