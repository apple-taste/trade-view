import { createContext, useContext, useState, useCallback, ReactNode, useEffect, useRef } from 'react';
import { Alert } from '../components/panels/AlertPanel';

interface AlertContextType {
  alerts: Alert[];
  addAlert: (alert: Omit<Alert, 'id' | 'timestamp'>) => void;
  dismissAlert: (alertId: string) => void;
  clearAllAlerts: () => void;
  clearAlertsByStockCode: (stockCode: string) => void; // 清除特定股票代码的所有提醒
  soundEnabled: boolean;  // 铃声开关
  toggleSound: () => void;  // 切换铃声
  volume: number;  // 音量（0-1）
  setVolume: (volume: number) => void;  // 设置音量
  playAlertSound: () => void;  // 播放提醒音效
}

const AlertContext = createContext<AlertContextType | undefined>(undefined);

export function AlertProvider({ children }: { children: ReactNode }) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(() => {
    // 从localStorage读取铃声开关状态
    const saved = localStorage.getItem('alertSoundEnabled');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const [volume, setVolumeState] = useState<number>(() => {
    // 从localStorage读取音量
    const saved = localStorage.getItem('alertVolume');
    return saved !== null ? parseFloat(saved) : 0.5;
  });
  
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const loopIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioContextRef = useRef<AudioContext | null>(null);  // 持久化AudioContext，确保音量控制生效
  const volumeRef = useRef<number>(volume);  // 使用ref存储音量，确保获取最新值
  const soundEnabledRef = useRef<boolean>(soundEnabled);  // 使用ref存储音效开关状态
  
  // 初始化音频（可选，如果jojo-alert.mp3存在）
  useEffect(() => {
    // 尝试加载自定义音频，但不强制要求
    const audio = new Audio('/jojo-alert.mp3');
    audio.volume = volume;
    
    // 监听加载错误 - 静默失败，使用内置音效
    audio.addEventListener('error', () => {
      // 不再输出警告，直接使用内置音效
      audioRef.current = null;
    });
    
    audio.addEventListener('canplaythrough', () => {
      // 只有成功加载才设置引用和输出日志
      console.log('✅ 使用自定义JOJO音频文件');
      audioRef.current = audio;
    });
    
    // 尝试加载（不阻塞）
    audio.load();
    
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);
  
  // 同步 ref 值
  useEffect(() => {
    volumeRef.current = volume;
    soundEnabledRef.current = soundEnabled;
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
  }, [volume, soundEnabled]);
  
  // Giorno's Theme（黄金体验镇魂曲）经典旋律片段
  const playGiornoTheme = useCallback(() => {
    // 从 ref 获取最新值，避免闭包问题
    const currentVolume = volumeRef.current;
    const currentSoundEnabled = soundEnabledRef.current;
    
    // 检查音效是否启用
    if (!currentSoundEnabled || currentVolume === 0) {
      return;
    }
    
    // 完全静默处理，不输出任何错误（浏览器autoplay policy限制）
    try {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioContextClass) return;
      
      // 使用持久化的AudioContext，确保音量控制生效
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContextClass();
      }
      const audioContext = audioContextRef.current;
      
      // 静默尝试恢复AudioContext（捕获Promise rejection）
      if (audioContext.state === 'suspended') {
        audioContext.resume().catch(() => {});
      }
      
      // 创建音符播放函数 - 包裹所有可能失败的操作
      const playNote = (frequency: number, startTime: number, duration: number, gain: number = 0.3) => {
        try {
          const oscillator = audioContext.createOscillator();
          const gainNode = audioContext.createGain();
          
          oscillator.connect(gainNode);
          gainNode.connect(audioContext.destination);
          
          oscillator.frequency.value = frequency;
          oscillator.type = 'square';
          
          gainNode.gain.setValueAtTime(0, audioContext.currentTime + startTime);
          gainNode.gain.linearRampToValueAtTime(currentVolume * gain, audioContext.currentTime + startTime + 0.02);
          gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + startTime + duration);
          
          oscillator.start(audioContext.currentTime + startTime);
          oscillator.stop(audioContext.currentTime + startTime + duration);
        } catch (e) {
          // 静默失败 - AudioContext未激活时会抛出错误
        }
      };
      
      // Giorno's Theme 经典钢琴旋律
      const notes = [
        { freq: 392.00, time: 0,     duration: 0.15 },
        { freq: 493.88, time: 0.15,  duration: 0.15 },
        { freq: 587.33, time: 0.3,   duration: 0.15 },
        { freq: 493.88, time: 0.45,  duration: 0.15 },
        { freq: 659.25, time: 0.6,   duration: 0.3  },
        { freq: 587.33, time: 0.9,   duration: 0.15 },
        { freq: 493.88, time: 1.05,  duration: 0.15 },
        { freq: 392.00, time: 1.2,   duration: 0.4  },
      ];
      
      notes.forEach(note => {
        playNote(note.freq, note.time, note.duration, 0.25);
      });
      
      // 低音和弦
      playNote(196.00, 0, 0.6, 0.15);
      playNote(196.00, 0.6, 0.6, 0.15);
      playNote(196.00, 1.2, 0.6, 0.15);
      
    } catch (error) {
      // 完全静默 - 不输出任何日志
    }
  }, []);
  
  // 使用Web Audio API生成JOJO黄金之风Giorno's Theme风格音效（循环播放）
  const playBuiltInSoundLoop = useCallback(() => {
    // 先清除可能存在的旧定时器
    if (loopIntervalRef.current) {
      clearInterval(loopIntervalRef.current);
      loopIntervalRef.current = null;
    }
    
    // 立即播放一次
    playGiornoTheme();
    
    // 然后每3秒循环播放一次，直到用户响应
    loopIntervalRef.current = setInterval(() => {
      // 从 ref 获取最新状态
      const currentVolume = volumeRef.current;
      const currentSoundEnabled = soundEnabledRef.current;
      
      if (currentSoundEnabled && currentVolume > 0) {
        playGiornoTheme();
      }
    }, 3000);
  }, [playGiornoTheme]);
  
  const playAlertSound = useCallback(() => {
    // 从 ref 获取最新值
    const currentVolume = volumeRef.current;
    const currentSoundEnabled = soundEnabledRef.current;
    
    // 检查音效是否启用
    if (!currentSoundEnabled) {
      console.log('🔇 音效已关闭');
      return;
    }
    
    // 检查音量
    if (currentVolume === 0) {
      console.log('🔇 音量为0');
      return;
    }
    
    setIsPlaying(true);
    
    // 如果有自定义音频文件，使用它
    if (audioRef.current) {
      audioRef.current.volume = currentVolume;
      audioRef.current.currentTime = 0;
      audioRef.current.play().catch(() => {
        // 静默降级到Web Audio API
        playBuiltInSoundLoop();
      });
    } else {
      // 使用Web Audio API生成JOJO风格音效，循环播放
      playBuiltInSoundLoop();
    }
  }, [playBuiltInSoundLoop]);
  
  // 停止循环播放
  const stopAlertSound = useCallback(() => {
    setIsPlaying(false);
    if (loopIntervalRef.current) {
      clearInterval(loopIntervalRef.current);
      loopIntervalRef.current = null;
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
  }, []);
  
  const toggleSound = useCallback(() => {
    setSoundEnabled(prev => {
      const newValue = !prev;
      localStorage.setItem('alertSoundEnabled', JSON.stringify(newValue));
      return newValue;
    });
  }, []);
  
  const setVolume = useCallback((newVolume: number) => {
    const clampedVolume = Math.max(0, Math.min(1, newVolume));
    setVolumeState(clampedVolume);
    localStorage.setItem('alertVolume', clampedVolume.toString());
  }, []);

  const addAlert = useCallback((alert: Omit<Alert, 'id' | 'timestamp'>) => {
    const newAlert: Alert = {
      ...alert,
      id: `${alert.stockCode}-${alert.type}-${Date.now()}`,
      timestamp: new Date(),
    };
    
    setAlerts(prev => {
      // 避免重复提醒（相同股票相同类型在5秒内的提醒）
      const recentAlert = prev.find(
        a => a.stockCode === alert.stockCode &&
             a.type === alert.type &&
             (Date.now() - a.timestamp.getTime()) < 5000
      );
      
      if (recentAlert) {
        return prev; // 不添加重复提醒
      }
      
      // 播放铃声
      playAlertSound();
      
      return [newAlert, ...prev].slice(0, 10); // 最多保留10条提醒
    });
  }, [playAlertSound]);

  const dismissAlert = useCallback((alertId: string) => {
    setAlerts(prev => {
      const newAlerts = prev.filter(alert => alert.id !== alertId);
      // 如果删除后没有提醒了，停止播放
      if (newAlerts.length === 0) {
        stopAlertSound();
      }
      return newAlerts;
    });
  }, [stopAlertSound]);

  const clearAllAlerts = useCallback(() => {
    setAlerts([]);
    stopAlertSound(); // 清除所有提醒时停止播放
  }, [stopAlertSound]);

  const clearAlertsByStockCode = useCallback((stockCode: string) => {
    setAlerts(prev => {
      const newAlerts = prev.filter(alert => alert.stockCode !== stockCode);
      // 如果删除后没有提醒了，停止播放
      if (newAlerts.length === 0) {
        stopAlertSound();
      }
      return newAlerts;
    });
  }, [stopAlertSound]);

  // 清理循环播放
  useEffect(() => {
    return () => {
      if (loopIntervalRef.current) {
        clearInterval(loopIntervalRef.current);
      }
    };
  }, []);
  
  return (
    <AlertContext.Provider
      value={{
        alerts,
        addAlert,
        dismissAlert,
        clearAllAlerts,
        clearAlertsByStockCode,
        soundEnabled,
        toggleSound,
        volume,
        setVolume,
        playAlertSound,
      }}
    >
      {children}
    </AlertContext.Provider>
  );
}

export function useAlerts() {
  const context = useContext(AlertContext);
  if (context === undefined) {
    throw new Error('useAlerts must be used within an AlertProvider');
  }
  return context;
}
