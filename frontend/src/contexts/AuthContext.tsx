import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { logger } from '../utils/logger';

interface User {
  id: number;
  username: string;
  email: string;
}

interface BillingStatus {
  billing_enabled: boolean;
  is_paid: boolean;
  paid_until?: string | null;
  plan?: string | null;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  billingStatus: BillingStatus | null;
  refreshBillingStatus: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const authTimeoutMs = 15000;

  useEffect(() => {
    logger.info('🔐 [Auth] 初始化认证上下文');
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
      logger.info('🔑 [Auth] 发现已保存的token，尝试恢复登录状态');
      setToken(savedToken);
      axios.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`;
      fetchUserProfile();
      fetchBillingStatus();
    } else {
      logger.info('ℹ️ [Auth] 未找到已保存的token');
      setLoading(false);
    }
  }, []);

  const fetchUserProfile = async () => {
    try {
      logger.info('📡 [Auth] 获取用户信息...');
      const response = await axios.get('/api/user/profile', { timeout: authTimeoutMs });
      logger.info('✅ [Auth] 用户信息获取成功', response.data);
      setUser(response.data);
    } catch (error: any) {
      logger.error('❌ [Auth] 获取用户信息失败', error.response?.data || error.message);
      localStorage.removeItem('token');
      setToken(null);
      setBillingStatus(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchBillingStatus = async () => {
    try {
      const res = await axios.get('/api/user/billing-status', { timeout: authTimeoutMs });
      setBillingStatus(res.data);
    } catch {
      setBillingStatus(null);
    }
  };

  const login = async (username: string, password: string) => {
    try {
      logger.info(`🔑 [Auth] 尝试登录用户: ${username}`);
      const response = await axios.post('/api/auth/login', { username, password }, { timeout: authTimeoutMs });
      const { token: newToken, user: userData } = response.data;
      logger.info('✅ [Auth] 登录成功', { userId: userData.id, username: userData.username });
      setToken(newToken);
      setUser(userData);
      localStorage.setItem('token', newToken);
      axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
      await fetchBillingStatus();
    } catch (error: any) {
      logger.error('❌ [Auth] 登录失败', error.response?.data || error.message);
      throw error;
    }
  };

  const register = async (username: string, email: string, password: string) => {
    try {
      logger.info(`📝 [Auth] 尝试注册用户: ${username} (${email})`);
      const response = await axios.post('/api/auth/register', { username, email, password }, { timeout: authTimeoutMs });
      const { token: newToken, user: userData } = response.data;
      logger.info('✅ [Auth] 注册成功', { userId: userData.id, username: userData.username });
      setToken(newToken);
      setUser(userData);
      localStorage.setItem('token', newToken);
      axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
      await fetchBillingStatus();
    } catch (error: any) {
      logger.error('❌ [Auth] 注册失败', error.response?.data || error.message);
      throw error;
    }
  };

  const logout = () => {
    logger.info('🚪 [Auth] 用户登出');
    setToken(null);
    setUser(null);
    setBillingStatus(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, token, billingStatus, refreshBillingStatus: fetchBillingStatus, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
