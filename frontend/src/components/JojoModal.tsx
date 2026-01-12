import { useEffect, useState } from 'react';
import { X } from 'lucide-react';

interface JojoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (value?: string) => void;
  title: string;
  message: string;
  type: 'confirm' | 'prompt';
  defaultValue?: string;
  placeholder?: string;
}

export default function JojoModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  type,
  defaultValue = '',
  placeholder = ''
}: JojoModalProps) {
  const [inputValue, setInputValue] = useState(defaultValue);

  useEffect(() => {
    if (isOpen) {
      setInputValue(defaultValue);
    }
  }, [isOpen, defaultValue]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm(type === 'prompt' ? inputValue : undefined);
    onClose();
  };

  const handleCancel = () => {
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && type === 'prompt') {
      handleConfirm();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 animate-fadeIn" style={{ zIndex: 9999 }}>
      {/* 背景遮罩 - JOJO深蓝色调 */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        style={{ zIndex: 9998 }}
        onClick={handleCancel}
      />

      {/* 弹窗内容 */}
      <div
        className="relative bg-gradient-to-br from-jojo-blue via-jojo-blue-dark to-jojo-blue-darker rounded-xl border-4 border-jojo-gold shadow-2xl shadow-jojo-gold/30 max-w-md w-full animate-scaleIn"
        style={{
          zIndex: 10000,
          boxShadow: '0 0 50px rgba(255, 215, 0, 0.4), 0 0 100px rgba(255, 215, 0, 0.2)',
        }}
      >
        {/* 标题栏 */}
        <div className="flex items-center justify-between p-4 border-b-2 border-jojo-gold bg-gradient-to-r from-jojo-gold/10 to-transparent">
          <h2 className="jojo-title text-2xl flex items-center space-x-2">
            <span className="text-3xl">⭐</span>
            <span>{title}</span>
          </h2>
          <button
            onClick={handleCancel}
            className="text-gray-400 hover:text-jojo-gold transition-colors"
            title="关闭 (Esc)"
          >
            <X size={24} />
          </button>
        </div>

        {/* 消息内容 */}
        <div className="p-6">
          <p className="text-gray-200 text-lg leading-relaxed whitespace-pre-line mb-6">
            {message}
          </p>

          {/* 输入框（仅在 prompt 模式下显示） */}
          {type === 'prompt' && (
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              autoFocus
              className="w-full px-4 py-3 bg-jojo-blue-darker border-2 border-jojo-gold/50 rounded-lg text-white text-lg focus:outline-none focus:border-jojo-gold transition-all"
              style={{
                boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.3)',
              }}
            />
          )}
        </div>

        {/* 按钮区域 */}
        <div className="flex items-center justify-end space-x-4 p-6 pt-0">
          <button
            onClick={handleCancel}
            className="px-6 py-3 bg-gray-600 hover:bg-gray-500 text-white font-bold rounded-lg border-2 border-gray-500 hover:border-gray-400 transition-all shadow-lg hover:shadow-xl text-lg"
          >
            取消
          </button>
          <button
            onClick={handleConfirm}
            className="px-6 py-3 bg-gradient-to-r from-jojo-gold to-yellow-500 hover:from-yellow-500 hover:to-jojo-gold text-jojo-blue font-bold rounded-lg border-2 border-yellow-600 hover:border-yellow-500 transition-all shadow-lg hover:shadow-2xl hover:shadow-jojo-gold/50 text-lg animate-pulse"
            style={{
              textShadow: '1px 1px 2px rgba(0, 0, 0, 0.5)',
            }}
          >
            确定
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
            transform: scale(0.9) translateY(-20px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }
        
        .animate-fadeIn {
          animation: fadeIn 0.2s ease-out;
        }
        
        .animate-scaleIn {
          animation: scaleIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
      `}</style>
    </div>
  );
}

// 使用Hook简化调用
export function useJojoModal() {
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    type: 'confirm' | 'prompt';
    defaultValue?: string;
    placeholder?: string;
    resolve?: (value: string | boolean | null) => void;
  }>({
    isOpen: false,
    title: '',
    message: '',
    type: 'confirm',
  });

  const confirm = (title: string, message: string): Promise<boolean> => {
    return new Promise((resolve) => {
      setModalState({
        isOpen: true,
        title,
        message,
        type: 'confirm',
        resolve: (value) => resolve(value === true),
      });
    });
  };

  const prompt = (
    title: string,
    message: string,
    defaultValue = '',
    placeholder = ''
  ): Promise<string | null> => {
    return new Promise((resolve) => {
      setModalState({
        isOpen: true,
        title,
        message,
        type: 'prompt',
        defaultValue,
        placeholder,
        resolve: (value) => resolve(value as string | null),
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

  const handleConfirm = (value?: string) => {
    const resolveFunc = modalState.resolve;
    const currentType = modalState.type;
    setModalState((prev) => ({ ...prev, isOpen: false, resolve: undefined }));
    if (resolveFunc) {
      if (currentType === 'confirm') {
        resolveFunc(true);
      } else {
        resolveFunc(value || null);
      }
    }
  };

  const Modal = () => (
    <JojoModal
      isOpen={modalState.isOpen}
      onClose={handleClose}
      onConfirm={handleConfirm}
      title={modalState.title}
      message={modalState.message}
      type={modalState.type}
      defaultValue={modalState.defaultValue}
      placeholder={modalState.placeholder}
    />
  );

  return {
    confirm,
    prompt,
    Modal,
  };
}
