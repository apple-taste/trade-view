import { Navigate } from 'react-router-dom';

export default function AdminPrivateRoute({ children }: { children: React.ReactNode }) {
  const adminToken = localStorage.getItem('adminToken');
  return adminToken ? <>{children}</> : <Navigate to="/admin/login" />;
}

