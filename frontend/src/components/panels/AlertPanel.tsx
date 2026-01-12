import { useEffect, useState } from 'react';
import { Bell, X, TrendingUp, TrendingDown, Volume2, VolumeX } from 'lucide-react';
import { useAlerts } from '../../contexts/AlertContext';

export interface Alert {
  id: string;
  type: 'stop_loss' | 'take_profit';
  stockCode: string;
  stockName?: string;
  currentPrice: number;
  targetPrice: number;
  timestamp: Date;
}

interface AlertPanelProps {
  alerts: Alert[];
  onDismiss: (alertId: string) => void;
  onClearAll: () => void;
}

export default function AlertPanel({ alerts, onDismiss, onClearAll }: AlertPanelProps) {
  const { soundEnabled, toggleSound, volume, setVolume, playAlertSound } = useAlerts();
  const [showVolumeSlider, setShowVolumeSlider] = useState(false);
  const [audioActivated, setAudioActivated] = useState(false);

  // 激活/停用音频上下文（toggle按钮）
  const toggleAudio = () => {
    if (audioActivated) {
      // 停用音频
      setAudioActivated(false);
    } else {
      // 激活音频
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioContextClass) {
        const ctx = new AudioContextClass();
        ctx.resume().then(() => {
          setAudioActivated(true);
          // 播放一次测试音效
          if (playAlertSound) {
            playAlertSound();
          }
        }).catch(() => {
          alert('无法激活音频，请点击页面任意位置后重试');
        });
      }
    }
  };


  if (alerts.length === 0) {
    return null;
  }

  return (
    <div className="jojo-card p-4 mb-4 border-4 border-yellow-400 animate-pulse">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Bell className="text-yellow-400 animate-bounce" size={24} />
          <h3 className="jojo-title text-xl">价格提醒</h3>
          <span className="px-2 py-1 bg-yellow-400 text-jojo-blue rounded-full text-sm font-bold">
            {alerts.length}
          </span>
          <span className="text-xs text-yellow-300 animate-pulse">🎵 循环播放中...</span>
        </div>
        <div className="flex items-center space-x-2">
          {/* 音频激活按钮 */}
          <button
            onClick={toggleAudio}
            className={`px-3 py-1.5 text-white text-xs font-semibold rounded-lg border-2 transition-all shadow-lg ${
              audioActivated
                ? 'bg-green-600 hover:bg-green-500 border-green-400 hover:shadow-green-500/50'
                : 'bg-purple-600 hover:bg-purple-500 border-purple-400 hover:shadow-purple-500/50'
            }`}
            title={audioActivated ? '点击停用音频' : '点击激活音频（解决浏览器自动播放限制）'}
          >
            {audioActivated ? '✓ 音频已启用' : '🎵 激活音频'}
          </button>
          
          {/* 铃声开关按钮 */}
          <div className="relative">
            <button
              onClick={toggleSound}
              className={`p-2 rounded transition-colors ${
                soundEnabled
                  ? 'text-jojo-gold hover:text-jojo-gold-dark border border-jojo-gold'
                  : 'text-gray-500 hover:text-gray-400 border border-gray-600'
              }`}
              title={soundEnabled ? '关闭铃声' : '开启铃声'}
            >
              {soundEnabled ? <Volume2 size={20} /> : <VolumeX size={20} />}
            </button>
            {soundEnabled && (
              <button
                onClick={() => setShowVolumeSlider(!showVolumeSlider)}
                className="ml-1 text-xs text-jojo-gold hover:text-jojo-gold-dark"
                title="调整音量"
              >
                {Math.round(volume * 100)}%
              </button>
            )}
            {/* 音量滑块 */}
            {showVolumeSlider && soundEnabled && (
              <div className="absolute top-full mt-2 right-0 bg-jojo-blue-dark border-2 border-jojo-gold rounded-lg p-3 shadow-lg z-50 w-48">
                <label className="block text-xs text-jojo-gold mb-2">
                  音量: {Math.round(volume * 100)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={Math.round(volume * 100)}
                  onChange={(e) => setVolume(parseInt(e.target.value) / 100)}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                  style={{
                    background: `linear-gradient(to right, #FFD700 0%, #FFD700 ${volume * 100}%, #374151 ${volume * 100}%, #374151 100%)`
                  }}
                />
              </div>
            )}
          </div>
          <button
            onClick={onClearAll}
            className="text-gray-400 hover:text-white text-sm px-3 py-1 border border-gray-600 rounded hover:border-gray-400"
          >
            清除全部
          </button>
        </div>
      </div>

      <div className="space-y-2 max-h-60 overflow-y-auto">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className={`p-3 rounded-lg border-2 flex items-center justify-between ${
              alert.type === 'take_profit'
                ? 'bg-green-500/20 border-green-400'
                : 'bg-red-500/20 border-red-400'
            }`}
          >
            <div className="flex items-center space-x-3 flex-1">
              {alert.type === 'take_profit' ? (
                <TrendingUp className="text-green-400" size={24} />
              ) : (
                <TrendingDown className="text-red-400" size={24} />
              )}
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-white text-lg">
                    {alert.stockCode}
                  </span>
                  {alert.stockName && (
                    <span className="text-gray-300 text-sm">- {alert.stockName}</span>
                  )}
                </div>
                <div className="text-sm text-gray-300 mt-1">
                  {alert.type === 'take_profit' ? '🎉 止盈提醒' : '⚠️ 止损提醒'}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  当前价格: <span className="font-bold text-white">¥{alert.currentPrice.toFixed(2)}</span>
                  {' | '}
                  目标价格: <span className="font-bold text-white">¥{alert.targetPrice.toFixed(2)}</span>
                  {' | '}
                  {alert.timestamp.toLocaleTimeString('zh-CN')}
                </div>
              </div>
            </div>
            <button
              onClick={() => onDismiss(alert.id)}
              className="ml-4 text-gray-400 hover:text-white transition-colors"
              title="关闭提醒"
            >
              <X size={20} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
