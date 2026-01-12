// 前端日志工具
const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
} as const;

type LogLevel = keyof typeof LOG_LEVELS;

class Logger {
  private level: number;

  constructor() {
    this.level = LOG_LEVELS.INFO;
  }

  private formatMessage(level: string, message: string, data?: any): string {
    const timestamp = new Date().toLocaleTimeString('zh-CN');
    const emoji = {
      DEBUG: '🔍',
      INFO: 'ℹ️',
      WARN: '⚠️',
      ERROR: '❌',
    }[level] || '📝';
    
    let logMessage = `[${timestamp}] ${emoji} [${level}] ${message}`;
    
    if (data) {
      logMessage += `\n数据: ${JSON.stringify(data, null, 2)}`;
    }
    
    return logMessage;
  }

  debug(message: string, data?: any) {
    if (this.level <= LOG_LEVELS.DEBUG) {
      console.log(this.formatMessage('DEBUG', message, data));
    }
  }

  info(message: string, data?: any) {
    if (this.level <= LOG_LEVELS.INFO) {
      console.log(this.formatMessage('INFO', message, data));
    }
  }

  warn(message: string, data?: any) {
    if (this.level <= LOG_LEVELS.WARN) {
      console.warn(this.formatMessage('WARN', message, data));
    }
  }

  error(message: string, error?: any) {
    if (this.level <= LOG_LEVELS.ERROR) {
      console.error(this.formatMessage('ERROR', message, error));
    }
  }

  setLevel(level: LogLevel) {
    this.level = LOG_LEVELS[level];
  }
}

export const logger = new Logger();

// 在开发环境下显示所有日志
if ((import.meta as any).env?.DEV) {
  logger.setLevel('DEBUG');
}
