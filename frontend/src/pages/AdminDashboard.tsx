import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { LogOut, RefreshCcw, Search, Users } from 'lucide-react';

type AdminStats = {
  total_users: number;
  new_users_7d: number;
  active_users_7d: number;
  paid_users: number;
  total_revenue: number;
};

type AdminUser = {
  id: number;
  username: string;
  email: string;
  created_at?: string;
  last_login_at?: string;
  is_paid: boolean;
  paid_until?: string | null;
  plan?: string | null;
  total_paid: number;
};

type PaginatedUsers = {
  items: AdminUser[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

function getAdminHeaders() {
  const token = localStorage.getItem('adminToken');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function formatDateTime(input?: string) {
  if (!input) return '-';
  const d = new Date(input);
  if (Number.isNaN(d.getTime())) return '-';
  return d.toLocaleString();
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);

  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [users, setUsers] = useState<PaginatedUsers | null>(null);
  const [loadingUsers, setLoadingUsers] = useState(false);

  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [savingUser, setSavingUser] = useState(false);
  const [editError, setEditError] = useState('');

  const logout = useCallback(() => {
    localStorage.removeItem('adminToken');
    navigate('/admin/login');
  }, [navigate]);

  const fetchStats = useCallback(async () => {
    setLoadingStats(true);
    try {
      const res = await axios.get('/api/admin/stats', { headers: getAdminHeaders() });
      setStats(res.data);
    } catch (err: any) {
      const status = err.response?.status;
      if (status === 401 || status === 403) {
        logout();
      }
    } finally {
      setLoadingStats(false);
    }
  }, [logout]);

  const fetchUsers = useCallback(async () => {
    setLoadingUsers(true);
    try {
      const res = await axios.get('/api/admin/users', {
        params: { query: query || undefined, page, page_size: pageSize },
        headers: getAdminHeaders(),
      });
      setUsers(res.data);
    } catch (err: any) {
      const status = err.response?.status;
      if (status === 401 || status === 403) {
        logout();
      }
    } finally {
      setLoadingUsers(false);
    }
  }, [logout, page, pageSize, query]);

  useEffect(() => {
    if (!localStorage.getItem('adminToken')) {
      navigate('/admin/login');
      return;
    }
    fetchStats();
    fetchUsers();
  }, [fetchStats, fetchUsers, navigate]);

  const cards = useMemo(() => {
    if (!stats) return [];
    return [
      { label: '注册用户', value: stats.total_users },
      { label: '近7天新增', value: stats.new_users_7d },
      { label: '近7天活跃', value: stats.active_users_7d },
      { label: '付费用户', value: stats.paid_users },
      { label: '累计收入', value: stats.total_revenue.toFixed(2) },
    ];
  }, [stats]);

  const handleSaveUser = async () => {
    if (!editing) return;
    setSavingUser(true);
    setEditError('');
    try {
      const payload = {
        is_paid: editing.is_paid,
        plan: editing.plan ?? undefined,
        paid_until: editing.paid_until === '' ? null : editing.paid_until ?? undefined,
        total_paid: Number.isFinite(editing.total_paid) ? editing.total_paid : undefined,
      };
      const res = await axios.patch(`/api/admin/users/${editing.id}`, payload, { headers: getAdminHeaders() });
      const updated = res.data as AdminUser;
      setEditing(updated);
      await fetchStats();
      await fetchUsers();
      setEditing(null);
    } catch (err: any) {
      setEditError(err.response?.data?.detail || '保存失败');
    } finally {
      setSavingUser(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-4">
      <div className="max-w-6xl mx-auto space-y-4">
        <div className="jojo-card p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users size={18} className="text-jojo-gold" />
            <h1 className="jojo-title text-lg">用户管理面板</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                fetchStats();
                fetchUsers();
              }}
              className="jojo-button flex items-center gap-1 text-xs px-2 py-1"
              disabled={loadingStats || loadingUsers}
            >
              <RefreshCcw size={14} />
              <span>刷新</span>
            </button>
            <button onClick={logout} className="jojo-button-danger flex items-center gap-1 text-xs px-2 py-1">
              <LogOut size={14} />
              <span>退出</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {cards.map((c) => (
            <div key={c.label} className="jojo-card p-3">
              <div className="text-xs text-gray-400">{c.label}</div>
              <div className="text-xl font-bold">{loadingStats ? '…' : c.value}</div>
            </div>
          ))}
        </div>

        <div className="jojo-card p-4">
          <div className="flex flex-col md:flex-row md:items-center gap-2 justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setPage(1);
                  }}
                  placeholder="搜索用户名/邮箱"
                  className="pl-8 pr-3 py-2 rounded bg-gray-900 border border-gray-700 text-white w-64"
                />
              </div>
              <div className="text-xs text-gray-400">
                {users ? `共 ${users.total} 人` : ''}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                className="jojo-button px-3 py-1 text-xs disabled:opacity-50"
                disabled={!users || users.page <= 1 || loadingUsers}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                上一页
              </button>
              <div className="text-xs text-gray-300">
                {users ? `${users.page} / ${users.total_pages}` : '…'}
              </div>
              <button
                className="jojo-button px-3 py-1 text-xs disabled:opacity-50"
                disabled={!users || users.page >= users.total_pages || loadingUsers}
                onClick={() => setPage((p) => (users ? Math.min(users.total_pages, p + 1) : p))}
              >
                下一页
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-800">
                  <th className="py-2 pr-3">用户</th>
                  <th className="py-2 pr-3">注册时间</th>
                  <th className="py-2 pr-3">最近登录</th>
                  <th className="py-2 pr-3">付费</th>
                  <th className="py-2 pr-3">套餐</th>
                  <th className="py-2 pr-3">到期</th>
                  <th className="py-2 pr-3">累计付费</th>
                  <th className="py-2 pr-3">操作</th>
                </tr>
              </thead>
              <tbody>
                {loadingUsers && (
                  <tr>
                    <td className="py-3 text-gray-400" colSpan={8}>
                      加载中…
                    </td>
                  </tr>
                )}
                {!loadingUsers && users?.items?.length === 0 && (
                  <tr>
                    <td className="py-3 text-gray-400" colSpan={8}>
                      暂无数据
                    </td>
                  </tr>
                )}
                {!loadingUsers &&
                  users?.items?.map((u) => (
                    <tr key={u.id} className="border-b border-gray-900">
                      <td className="py-2 pr-3">
                        <div className="font-semibold">{u.username}</div>
                        <div className="text-xs text-gray-400">{u.email}</div>
                      </td>
                      <td className="py-2 pr-3">{formatDateTime(u.created_at)}</td>
                      <td className="py-2 pr-3">{formatDateTime(u.last_login_at)}</td>
                      <td className="py-2 pr-3">{u.is_paid ? '是' : '否'}</td>
                      <td className="py-2 pr-3">{u.plan || '-'}</td>
                      <td className="py-2 pr-3">{u.paid_until || '-'}</td>
                      <td className="py-2 pr-3">{Number(u.total_paid || 0).toFixed(2)}</td>
                      <td className="py-2 pr-3">
                        <button className="jojo-button px-2 py-1 text-xs" onClick={() => setEditing(u)}>
                          编辑
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {editing && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <div className="jojo-card w-full max-w-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="jojo-title text-base">编辑用户</div>
                <div className="text-xs text-gray-400">
                  {editing.username} · {editing.email}
                </div>
              </div>
              <button className="text-gray-400 hover:text-white" onClick={() => setEditing(null)}>
                关闭
              </button>
            </div>

            {editError && <div className="mb-3 text-red-300 text-sm">{editError}</div>}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={editing.is_paid}
                  onChange={(e) => setEditing((prev) => (prev ? { ...prev, is_paid: e.target.checked } : prev))}
                />
                <span>已付费</span>
              </label>

              <div>
                <div className="text-xs text-gray-400 mb-1">套餐</div>
                <input
                  value={editing.plan ?? ''}
                  onChange={(e) => setEditing((prev) => (prev ? { ...prev, plan: e.target.value } : prev))}
                  className="w-full px-3 py-2 rounded bg-gray-900 border border-gray-700 text-white"
                  placeholder="free / pro / ..."
                />
              </div>

              <div>
                <div className="text-xs text-gray-400 mb-1">到期日</div>
                <input
                  value={editing.paid_until ?? ''}
                  onChange={(e) => setEditing((prev) => (prev ? { ...prev, paid_until: e.target.value } : prev))}
                  className="w-full px-3 py-2 rounded bg-gray-900 border border-gray-700 text-white"
                  type="date"
                />
              </div>

              <div>
                <div className="text-xs text-gray-400 mb-1">累计付费</div>
                <input
                  value={String(editing.total_paid ?? 0)}
                  onChange={(e) => {
                    const v = Number(e.target.value);
                    setEditing((prev) => (prev ? { ...prev, total_paid: Number.isFinite(v) ? v : prev.total_paid } : prev));
                  }}
                  className="w-full px-3 py-2 rounded bg-gray-900 border border-gray-700 text-white"
                  type="number"
                  step="0.01"
                  min="0"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-4">
              <button className="jojo-button px-3 py-1 text-xs" onClick={() => setEditing(null)}>
                取消
              </button>
              <button
                className="jojo-button px-3 py-1 text-xs disabled:opacity-50"
                disabled={savingUser}
                onClick={handleSaveUser}
              >
                {savingUser ? '保存中…' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

