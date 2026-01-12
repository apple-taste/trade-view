import { useEffect, useState } from 'react';
import { X, TrendingUp, TrendingDown } from 'lucide-react';

interface JojoPriceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (result: { price: string; date?: string }) => void;
  type: 'take_profit' | 'stop_loss';
  stockCode: string;
  stockName?: string;
  currentPrice?: number;
  targetPrice?: number;
  defaultValue?: string;
}

export default function JojoPriceModal({
  isOpen,
  onClose,
  onConfirm,
  type,
  stockCode,
  stockName,
  currentPrice,
  targetPrice,
  defaultValue = ''
}: JojoPriceModalProps) {
  const [price, setPrice] = useState(defaultValue);
  const [closeDate, setCloseDate] = useState('');

  useEffect(() => {
    if (isOpen) {
      setPrice(defaultValue || targetPrice?.toString() || '');
      // 默认使用今天的日期（北京时间）
      const today = new Date();
      // 获取北京时间（UTC+8）
      const beijingOffset = 8 * 60 * 60 * 1000; // 8小时
      const utcTime = today.getTime() + (today.getTimezoneOffset() * 60 * 1000);
      const beijingTime = new Date(utcTime + beijingOffset);
      const dateStr = beijingTime.toISOString().split('T')[0];
      setCloseDate(dateStr);
    }
  }, [isOpen, defaultValue, targetPrice]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm({ price, date: closeDate || undefined });
    onClose();
  };

  const handleCancel = () => {
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleConfirm();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  const isTakeProfit = type === 'take_profit';
  const themeColor = isTakeProfit ? 'green' : 'red';
  const emoji = isTakeProfit ? '🎉' : '⚠️';
  const title = isTakeProfit ? '止盈订单' : '止损订单';
  const Icon = isTakeProfit ? TrendingUp : TrendingDown;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 animate-fadeIn" style={{ zIndex: 9999 }}>
      {/* 背景遮罩 - 简约 */}
      <div
        className="absolute inset-0 backdrop-blur-sm bg-black/70"
        style={{ zIndex: 9998 }}
        onClick={handleCancel}
      />

      {/* 弹窗内容 - 简约探险风 */}
      <div
        className={`relative rounded-xl border-3 shadow-2xl max-w-md w-full animate-scaleIn ${
          isTakeProfit
            ? 'bg-gradient-to-br from-green-900/90 to-jojo-blue-darker border-green-500'
            : 'bg-gradient-to-br from-red-900/90 to-jojo-blue-darker border-red-500'
        }`}
        style={{
          zIndex: 10000,
          boxShadow: isTakeProfit
            ? '0 0 40px rgba(16, 185, 129, 0.4)'
            : '0 0 40px rgba(239, 68, 68, 0.4)',
        }}
      >

        {/* 标题栏 - 简约风格 */}
        <div
          className={`relative flex items-center justify-between p-5 border-b-2 ${
            isTakeProfit
              ? 'border-green-500 bg-green-500/10'
              : 'border-red-500 bg-red-500/10'
          }`}
        >
          <div className="flex items-center space-x-3">
            <Icon className={isTakeProfit ? 'text-green-400' : 'text-red-400'} size={28} />
            <div>
              <h2 className="text-2xl font-bold text-white">
                {emoji} {title}
              </h2>
              <p className="text-sm text-gray-300">
                {stockCode} {stockName && `- ${stockName}`}
              </p>
            </div>
          </div>
          <button
            onClick={handleCancel}
            className="text-gray-400 hover:text-white transition-all"
            title="关闭 (Esc)"
          >
            <X size={24} />
          </button>
        </div>

        {/* 内容区域 - 简约设计 */}
        <div className="relative p-6 space-y-4">
          {/* 当前价格 */}
          {currentPrice && (
            <div className="flex justify-between items-center text-lg">
              <span className="text-gray-300">当前价格</span>
              <span className="text-white font-bold">¥{currentPrice.toFixed(2)}</span>
            </div>
          )}

          {/* 离场价格输入框 */}
          <div className="space-y-2">
            <label className="text-white font-bold text-lg">
              {isTakeProfit ? '🎯 止盈离场价格' : '🛡️ 止损离场价格'}
            </label>
            <div className="relative">
              <input
                type="text"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="例如: 15.50"
                autoFocus
                className={`w-full px-4 py-4 rounded-lg text-white text-2xl font-bold focus:outline-none transition-all placeholder-gray-500 ${
                  isTakeProfit
                    ? 'bg-green-900/50 border-2 border-green-500 focus:border-green-400'
                    : 'bg-red-900/50 border-2 border-red-500 focus:border-red-400'
                }`}
                style={{
                  textShadow: '0 0 8px rgba(255, 255, 255, 0.8)',
                }}
              />
              <div
                className={`absolute right-4 top-1/2 transform -translate-y-1/2 font-bold ${
                  isTakeProfit ? 'text-green-400' : 'text-red-400'
                }`}
              >
                ¥
              </div>
            </div>
          </div>

          {/* 离场日期选择 */}
          <div className="space-y-2">
            <label className="text-white font-bold text-lg">
              📅 离场日期（北京时间）
            </label>
            <div className="relative">
              <input
                type="date"
                value={closeDate}
                onChange={(e) => setCloseDate(e.target.value)}
                onKeyDown={handleKeyDown}
                className={`w-full px-4 py-4 rounded-lg text-white text-xl font-bold focus:outline-none transition-all ${
                  isTakeProfit
                    ? 'bg-green-900/50 border-2 border-green-500 focus:border-green-400'
                    : 'bg-red-900/50 border-2 border-red-500 focus:border-red-400'
                }`}
                style={{
                  textShadow: '0 0 8px rgba(255, 255, 255, 0.8)',
                }}
              />
            </div>
            <div className="text-sm text-gray-400 text-center">
              💡 留空则使用今天日期
            </div>
          </div>

          {/* 提示 */}
          <div className="text-sm text-gray-400 text-center">
            {isTakeProfit
              ? '💡 建议止盈价格高于买入价 6-10%'
              : '💡 建议止损价格低于买入价 3-5%'}
          </div>
        </div>

        {/* 按钮区域 - 简约清晰 */}
        <div className="relative flex items-center justify-center space-x-4 p-6 pt-2 pb-6">
          <button
            onClick={handleCancel}
            className="px-10 py-3 bg-gray-700 hover:bg-gray-600 text-white font-bold rounded-lg border-2 border-gray-600 hover:border-gray-500 transition-all shadow-lg hover:shadow-xl text-lg transform hover:scale-105"
          >
            取消
          </button>
          <button
            onClick={handleConfirm}
            className={`px-10 py-3 font-bold rounded-lg border-2 transition-all shadow-lg hover:shadow-xl text-lg transform hover:scale-105 ${
              isTakeProfit
                ? 'bg-green-600 hover:bg-green-500 text-white border-green-400'
                : 'bg-red-600 hover:bg-red-500 text-white border-red-400'
            }`}
            style={{
              textShadow: '1px 1px 2px rgba(0, 0, 0, 0.5)',
            }}
          >
            {isTakeProfit ? '✓ 确认止盈' : '✓ 确认止损'}
          </button>
        </div>
      </div>

      {/* 简约动画样式 */}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        @keyframes scaleIn {
          from {
            opacity: 0;
            transform: scale(0.9);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
        
        .animate-fadeIn {
          animation: fadeIn 0.2s ease-out;
        }
        
        .animate-scaleIn {
          animation: scaleIn 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}

// 使用Hook简化调用
export function useJojoPriceModal() {
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    type: 'take_profit' | 'stop_loss';
    stockCode: string;
    stockName?: string;
    currentPrice?: number;
    targetPrice?: number;
    defaultValue?: string;
    resolve?: (value: string | null) => void;
  }>({
    isOpen: false,
    type: 'take_profit',
    stockCode: '',
  });

  const openModal = (
    type: 'take_profit' | 'stop_loss',
    stockCode: string,
    stockName?: string,
    currentPrice?: number,
    targetPrice?: number,
    defaultValue?: string
  ): Promise<{ price: string; date?: string } | null> => {
    return new Promise((resolve) => {
      setModalState({
        isOpen: true,
        type,
        stockCode,
        stockName,
        currentPrice,
        targetPrice,
        defaultValue,
        resolve,
      });
    });
  };

  const handleClose = () => {
    const resolveFunc = modalState.resolve;
    setModalState((prev) => ({ ...prev, isOpen: false, resolve: undefined }));
    if (resolveFunc) {
      resolveFunc(null);
    }
  };

  const handleConfirm = (result: { price: string; date?: string }) => {
    const resolveFunc = modalState.resolve;
    setModalState((prev) => ({ ...prev, isOpen: false, resolve: undefined }));
    if (resolveFunc) {
      resolveFunc(result);
    }
  };

  const Modal = () => (
    <JojoPriceModal
      isOpen={modalState.isOpen}
      onClose={handleClose}
      onConfirm={handleConfirm}
      type={modalState.type}
      stockCode={modalState.stockCode}
      stockName={modalState.stockName}
      currentPrice={modalState.currentPrice}
      targetPrice={modalState.targetPrice}
      defaultValue={modalState.defaultValue}
    />
  );

  return {
    openModal,
    Modal,
  };
}
