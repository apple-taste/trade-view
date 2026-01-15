import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

// 生产环境调试日志
console.log('%c TradeView v1.1.3 Loaded ', 'background: #222; color: #bada55; font-size: 20px');
console.log('Build Time: ' + new Date().toISOString());;
