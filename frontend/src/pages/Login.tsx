import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Star, Sparkles, TrendingUp } from 'lucide-react';

export default function Login() {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      if (isLogin) {
        setSubmitting(true);
        await login(username, password);
      } else {
        if (!email) {
          setError('请填写邮箱');
          return;
        }
        setSubmitting(true);
        await register(username, email, password);
      }
      navigate('/');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg =
        (typeof detail === 'string' && detail) ||
        err?.response?.data?.error ||
        err?.message ||
        '操作失败';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center relative overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, #1a0f3d 0%, #0f0a24 50%, #1a0f3d 100%)',
      }}
    >
      {/* 背景装饰星星 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(30)].map((_, i) => (
          <Star
            key={i}
            className="absolute text-yellow-400 opacity-20 animate-pulse"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              width: `${Math.random() * 20 + 10}px`,
              height: `${Math.random() * 20 + 10}px`,
              animationDelay: `${Math.random() * 3}s`,
              animationDuration: `${Math.random() * 2 + 2}s`,
            }}
          />
        ))}
      </div>

      {/* 主容器 */}
      <div 
        className="max-w-md w-full mx-4 relative z-10"
        style={{
          animation: 'fadeInScale 0.6s ease-out',
        }}
      >
        <style>{`
          @keyframes fadeInScale {
            from {
              opacity: 0;
              transform: scale(0.9) translateY(20px);
            }
            to {
              opacity: 1;
              transform: scale(1) translateY(0);
            }
          }
          @keyframes shimmer {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 0.8; }
          }
          @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
          }
          .jojo-input:focus {
            box-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
          }
        `}</style>

        {/* 标题区域 */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-4">
            <TrendingUp 
              className="text-yellow-400 mr-3" 
              size={48}
              style={{ 
                filter: 'drop-shadow(0 0 15px rgba(255, 215, 0, 0.8))',
                animation: 'float 3s ease-in-out infinite'
              }}
            />
            <Sparkles 
              className="text-yellow-300 absolute animate-pulse" 
              size={24}
              style={{ 
                filter: 'drop-shadow(0 0 10px rgba(255, 215, 0, 0.6))',
                animation: 'shimmer 2s ease-in-out infinite'
              }}
            />
          </div>
          <h2 
            className="text-4xl font-black tracking-wider"
            style={{
              background: 'linear-gradient(135deg, #FFD700 0%, #FFA500 50%, #FFD700 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              textShadow: '0 0 30px rgba(255, 215, 0, 0.5)',
              fontFamily: '"Arial Black", sans-serif',
              letterSpacing: '0.1em',
            }}
          >
            交易管理系统
          </h2>
          <p className="text-yellow-200 mt-2 text-sm tracking-wide" style={{ textShadow: '0 0 10px rgba(255, 215, 0, 0.3)' }}>
            专注你的交易管理
          </p>
        </div>

        {/* 表单容器 */}
        <div 
          className="p-8 rounded-2xl relative"
          style={{
            background: 'linear-gradient(135deg, rgba(30, 20, 60, 0.95) 0%, rgba(20, 15, 40, 0.95) 100%)',
            border: '3px solid',
            borderImage: 'linear-gradient(135deg, #FFD700, #FFA500, #FFD700) 1',
            boxShadow: '0 0 40px rgba(255, 215, 0, 0.3), inset 0 0 30px rgba(255, 215, 0, 0.1)',
          }}
        >
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div 
                className="px-4 py-3 rounded-lg border-2 text-center font-bold"
                style={{
                  background: 'linear-gradient(135deg, rgba(220, 38, 38, 0.2), rgba(185, 28, 28, 0.2))',
                  borderColor: '#ef4444',
                  color: '#fca5a5',
                  textShadow: '0 0 10px rgba(239, 68, 68, 0.5)',
                }}
              >
                ⚠️ {error}
              </div>
            )}

            <div className="space-y-5">
              {/* 用户名输入 */}
              <div>
                <label 
                  htmlFor="username" 
                  className="block text-sm font-bold mb-2 tracking-wide"
                  style={{ 
                    color: '#FFD700',
                    textShadow: '0 0 10px rgba(255, 215, 0, 0.5)',
                  }}
                >
                  ⭐ 用户名
                </label>
                <input
                  id="username"
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="jojo-input w-full px-4 py-3 rounded-lg border-2 text-white font-semibold text-lg transition-all duration-300"
                  style={{
                    background: 'rgba(10, 5, 20, 0.8)',
                    borderColor: '#FFD700',
                    outline: 'none',
                  }}
                  placeholder="输入你的名字"
                />
              </div>

              {/* 邮箱输入（仅注册时显示） */}
              {!isLogin && (
                <div>
                  <label 
                    htmlFor="email" 
                    className="block text-sm font-bold mb-2 tracking-wide"
                    style={{ 
                      color: '#FFD700',
                      textShadow: '0 0 10px rgba(255, 215, 0, 0.5)',
                    }}
                  >
                    📧 邮箱
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="jojo-input w-full px-4 py-3 rounded-lg border-2 text-white font-semibold text-lg transition-all duration-300"
                    style={{
                      background: 'rgba(10, 5, 20, 0.8)',
                      borderColor: '#FFD700',
                      outline: 'none',
                    }}
                    placeholder="输入你的邮箱"
                  />
                </div>
              )}

              {/* 密码输入 */}
              <div>
                <label 
                  htmlFor="password" 
                  className="block text-sm font-bold mb-2 tracking-wide"
                  style={{ 
                    color: '#FFD700',
                    textShadow: '0 0 10px rgba(255, 215, 0, 0.5)',
                  }}
                >
                  🔐 密码
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="jojo-input w-full px-4 py-3 rounded-lg border-2 text-white font-semibold text-lg transition-all duration-300"
                  style={{
                    background: 'rgba(10, 5, 20, 0.8)',
                    borderColor: '#FFD700',
                    outline: 'none',
                  }}
                  placeholder="输入你的密码"
                />
              </div>
            </div>

            {/* 提交按钮 */}
            <div>
              <button
                type="submit"
                disabled={submitting}
                className="w-full py-4 rounded-xl font-black text-xl tracking-widest transition-all duration-300 hover:scale-105 active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed"
                style={{
                  background: 'linear-gradient(135deg, #FFD700 0%, #FFA500 50%, #FFD700 100%)',
                  color: '#1a0f3d',
                  textShadow: '0 2px 4px rgba(0, 0, 0, 0.3)',
                  boxShadow: '0 0 30px rgba(255, 215, 0, 0.6), inset 0 -3px 10px rgba(0, 0, 0, 0.3)',
                  border: '3px solid rgba(255, 255, 255, 0.3)',
                }}
              >
                {submitting ? (isLogin ? '登录中…' : '注册中…') : isLogin ? '🚀 开始冒险' : '✨ 创建账号'}
              </button>
            </div>

            {/* 切换按钮 */}
            <div className="text-center pt-4">
              <button
                type="button"
                disabled={submitting}
                onClick={() => {
                  setIsLogin(!isLogin);
                  setError('');
                }}
                className="text-sm font-bold tracking-wide transition-all duration-300 hover:scale-110 disabled:opacity-60 disabled:cursor-not-allowed"
                style={{
                  color: '#FFD700',
                  textShadow: '0 0 10px rgba(255, 215, 0, 0.5)',
                }}
              >
                {isLogin ? '🌟 没有账号？立即注册' : '🎯 已有账号？立即登录'}
              </button>
            </div>
          </form>
        </div>

        {/* 底部装饰 */}
        <div className="text-center mt-6 text-yellow-300 text-xs opacity-70" style={{ textShadow: '0 0 5px rgba(255, 215, 0, 0.3)' }}>
          ⭐ JoJo Land: Golden Adventure ⭐
        </div>
      </div>
    </div>
  );
}
