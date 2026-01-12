import { useEffect, useState } from 'react';
import { X, Sparkles, TrendingUp } from 'lucide-react';

interface JojoCapitalModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (capital: string, date: string) => void;
  defaultCapital?: string;
  defaultDate?: string;
}

export default function JojoCapitalModal({
  isOpen,
  onClose,
  onConfirm,
  defaultCapital = '',
  defaultDate = new Date().toISOString().split('T')[0]
}: JojoCapitalModalProps) {
  const [capital, setCapital] = useState(defaultCapital);
  const [date, setDate] = useState(defaultDate);

  useEffect(() => {
    if (isOpen) {
      setCapital(defaultCapital);
      setDate(defaultDate);
    }
  }, [isOpen, defaultCapital, defaultDate]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm(capital, date);
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

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 animate-fadeIn" style={{ zIndex: 9999 }}>
      {/* 背景遮罩 - 探险感的渐变 */}
      <div
        className="absolute inset-0 backdrop-blur-md animate-pulse-slow"
        style={{
          zIndex: 9998,
          background: 'radial-gradient(circle at center, rgba(255, 215, 0, 0.15) 0%, rgba(0, 0, 0, 0.9) 100%)',
        }}
        onClick={handleCancel}
      />

      {/* 弹窗内容 */}
      <div
        className="relative bg-gradient-to-br from-jojo-blue via-jojo-blue-dark to-jojo-blue-darker rounded-2xl border-4 shadow-2xl max-w-lg w-full animate-scaleIn overflow-hidden"
        style={{
          zIndex: 10000,
          borderImage: 'linear-gradient(135deg, #FFD700, #FFA500, #FFD700) 1',
          boxShadow: '0 0 60px rgba(255, 215, 0, 0.6), 0 0 100px rgba(255, 165, 0, 0.4), inset 0 0 30px rgba(255, 215, 0, 0.1)',
        }}
      >
        {/* 探险感的背景装饰 */}
        <div className="absolute inset-0 opacity-10 pointer-events-none">
          <div className="absolute top-0 left-0 w-full h-full" style={{
            backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255, 215, 0, 0.1) 10px, rgba(255, 215, 0, 0.1) 20px)',
          }} />
        </div>

        {/* 标题栏 */}
        <div className="relative flex items-center justify-between p-6 border-b-2 border-jojo-gold bg-gradient-to-r from-jojo-gold/20 via-jojo-gold/10 to-transparent">
          <div className="flex items-center space-x-3">
            <Sparkles className="text-jojo-gold animate-spin-slow" size={32} />
            <h2 className="jojo-title text-3xl flex items-center space-x-2 animate-pulse">
              <TrendingUp className="text-jojo-gold" size={28} />
              <span>💰 探险资金设置</span>
            </h2>
          </div>
          <button
            onClick={handleCancel}
            className="text-gray-400 hover:text-jojo-gold transition-all transform hover:rotate-90 hover:scale-110"
            title="关闭 (Esc)"
          >
            <X size={28} />
          </button>
        </div>

        {/* 消息内容 */}
        <div className="relative p-8 space-y-6">
          <div className="bg-jojo-gold/10 border-2 border-jojo-gold/30 rounded-lg p-4 animate-pulse-slow">
            <p className="text-gray-200 text-lg leading-relaxed">
              🌟 设置您的探险初始资金，开启财富冒险之旅！
            </p>
            <p className="text-gray-400 text-sm mt-2">
              系统将根据交易历史自动计算后续资金变化
            </p>
          </div>

          {/* 资金输入框 */}
          <div className="space-y-2">
            <label className="flex items-center space-x-2 text-jojo-gold font-bold text-lg">
              <span className="text-2xl">💵</span>
              <span>初始资金金额</span>
            </label>
            <div className="relative">
              <input
                type="text"
                value={capital}
                onChange={(e) => setCapital(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="例如: 100000"
                autoFocus
                className="w-full px-6 py-4 bg-gradient-to-r from-jojo-blue-darker to-jojo-blue-dark border-3 border-jojo-gold rounded-xl text-white text-2xl font-bold focus:outline-none focus:border-yellow-400 transition-all placeholder-gray-500 shadow-inner"
                style={{
                  boxShadow: 'inset 0 2px 8px rgba(0, 0, 0, 0.5), 0 0 20px rgba(255, 215, 0, 0.3)',
                  textShadow: '0 0 10px rgba(255, 255, 255, 0.5)',
                }}
              />
              <div className="absolute right-4 top-1/2 transform -translate-y-1/2 text-jojo-gold text-xl font-bold">
                CNY ¥
              </div>
            </div>
          </div>

          {/* 日期输入框 */}
          <div className="space-y-2">
            <label className="flex items-center space-x-2 text-jojo-gold font-bold text-lg">
              <span className="text-2xl">📅</span>
              <span>初始资金日期</span>
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full px-6 py-4 bg-gradient-to-r from-jojo-blue-darker to-jojo-blue-dark border-3 border-jojo-gold/70 rounded-xl text-white text-xl font-semibold focus:outline-none focus:border-jojo-gold transition-all shadow-inner"
              style={{
                boxShadow: 'inset 0 2px 8px rgba(0, 0, 0, 0.5), 0 0 15px rgba(255, 215, 0, 0.2)',
                colorScheme: 'dark',
              }}
            />
          </div>

          {/* 提示信息 */}
          <div className="flex items-start space-x-2 text-sm text-gray-400 bg-jojo-purple/20 border border-jojo-gold/20 rounded-lg p-3">
            <span className="text-yellow-400">💡</span>
            <p>留空日期则使用今天，系统会自动重新计算资金曲线</p>
          </div>
        </div>

        {/* 按钮区域 */}
        <div className="relative flex items-center justify-end space-x-4 p-6 pt-0 pb-8">
          <button
            onClick={handleCancel}
            className="px-8 py-4 bg-gray-700 hover:bg-gray-600 text-white font-bold rounded-xl border-3 border-gray-600 hover:border-gray-500 transition-all shadow-lg hover:shadow-xl text-lg transform hover:scale-105"
          >
            取消
          </button>
          <button
            onClick={handleConfirm}
            className="relative px-8 py-4 bg-gradient-to-r from-jojo-gold via-yellow-500 to-jojo-gold hover:from-yellow-500 hover:via-jojo-gold hover:to-yellow-500 text-jojo-blue font-bold rounded-xl border-3 border-yellow-600 hover:border-yellow-400 transition-all shadow-lg hover:shadow-2xl text-lg transform hover:scale-110 animate-pulse-glow overflow-hidden"
            style={{
              textShadow: '2px 2px 4px rgba(0, 0, 0, 0.5)',
              boxShadow: '0 0 30px rgba(255, 215, 0, 0.8), 0 0 60px rgba(255, 165, 0, 0.6)',
            }}
          >
            <span className="relative z-10 flex items-center space-x-2">
              <Sparkles size={20} />
              <span>确定探险</span>
              <TrendingUp size={20} />
            </span>
            {/* 闪光效果 */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shine" />
          </button>
        </div>
      </div>

      {/* 添加动画样式 */}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        @keyframes scaleIn {
          from {
            opacity: 0;
            transform: scale(0.8) translateY(-30px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }
        
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        @keyframes pulse-slow {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.8; }
        }
        
        @keyframes pulse-glow {
          0%, 100% {
            box-shadow: 0 0 30px rgba(255, 215, 0, 0.8), 0 0 60px rgba(255, 165, 0, 0.6);
          }
          50% {
            box-shadow: 0 0 40px rgba(255, 215, 0, 1), 0 0 80px rgba(255, 165, 0, 0.8);
          }
        }
        
        @keyframes shine {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(200%); }
        }
        
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
        
        .animate-scaleIn {
          animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        
        .animate-spin-slow {
          animation: spin-slow 3s linear infinite;
        }
        
        .animate-pulse-slow {
          animation: pulse-slow 2s ease-in-out infinite;
        }
        
        .animate-pulse-glow {
          animation: pulse-glow 2s ease-in-out infinite;
        }
        
        .animate-shine {
          animation: shine 3s ease-in-out infinite;
        }
        
        /* 改善日期选择器的样式 */
        input[type="date"]::-webkit-calendar-picker-indicator {
          filter: invert(1);
          cursor: pointer;
          font-size: 1.2em;
        }
      `}</style>
    </div>
  );
}

// 使用Hook简化调用
export function useJojoCapitalModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [resolve, setResolve] = useState<((value: { capital: string; date: string } | null) => void) | null>(null);

  const openModal = (defaultCapital = '', defaultDate = new Date().toISOString().split('T')[0]): Promise<{ capital: string; date: string } | null> => {
    return new Promise((res) => {
      setResolve(() => res);
      setIsOpen(true);
    });
  };

  const handleClose = () => {
    setIsOpen(false);
    if (resolve) {
      resolve(null);
      setResolve(null);
    }
  };

  const handleConfirm = (capital: string, date: string) => {
    if (resolve) {
      resolve({ capital, date });
      setResolve(null);
    }
    setIsOpen(false);
  };

  const Modal = () => (
    <JojoCapitalModal
      isOpen={isOpen}
      onClose={handleClose}
      onConfirm={handleConfirm}
      defaultCapital=""
      defaultDate={new Date().toISOString().split('T')[0]}
    />
  );

  return {
    openModal,
    Modal,
  };
}
