import { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Shield } from 'lucide-react';

export default function AdminLogin() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      const res = await axios.post('/api/admin/login', { username, password });
      const token = res.data?.token as string | undefined;
      if (!token) {
        setError('登录失败');
        return;
      }
      localStorage.setItem('adminToken', token);
      navigate('/admin');
    } catch (err: any) {
      setError(err.response?.data?.detail || '登录失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
      <div className="w-full max-w-md jojo-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="text-jojo-gold" size={18} />
          <h1 className="jojo-title text-lg">管理员登录</h1>
        </div>

        {error && <div className="mb-4 text-red-300 text-sm">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-300 mb-1">用户名</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 rounded bg-gray-900 border border-gray-700 text-white"
              autoComplete="username"
              required
            />
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1">密码</label>
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 rounded bg-gray-900 border border-gray-700 text-white"
              autoComplete="current-password"
              type="password"
              required
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="jojo-button w-full disabled:opacity-50"
          >
            {submitting ? '登录中…' : '登录'}
          </button>
        </form>
      </div>
    </div>
  );
}

