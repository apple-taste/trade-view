import { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { TradeProvider } from './contexts/TradeContext';
import { AlertProvider } from './contexts/AlertContext';
import { LocaleProvider } from './contexts/LocaleContext';
import PrivateRoute from './components/PrivateRoute';
import AdminPrivateRoute from './components/AdminPrivateRoute';

const Login = lazy(() => import('./pages/Login'));
const AdminLogin = lazy(() => import('./pages/AdminLogin'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Billing = lazy(() => import('./pages/Billing'));

const fallback = (
  <div className="min-h-screen flex items-center justify-center text-gray-400 text-sm">
    加载中...
  </div>
);

function App() {
  return (
    <LocaleProvider>
      <AuthProvider>
        <TradeProvider>
          <AlertProvider>
            <Router
              future={{
                v7_startTransition: true,
                v7_relativeSplatPath: true,
              }}
            >
              <Routes>
                <Route
                  path="/login"
                  element={
                    <Suspense fallback={fallback}>
                      <Login />
                    </Suspense>
                  }
                />
                <Route
                  path="/billing"
                  element={
                    <PrivateRoute>
                      <Suspense fallback={fallback}>
                        <Billing />
                      </Suspense>
                    </PrivateRoute>
                  }
                />
                <Route
                  path="/admin/login"
                  element={
                    <Suspense fallback={fallback}>
                      <AdminLogin />
                    </Suspense>
                  }
                />
                <Route
                  path="/admin/*"
                  element={
                    <AdminPrivateRoute>
                      <Suspense fallback={fallback}>
                        <AdminDashboard />
                      </Suspense>
                    </AdminPrivateRoute>
                  }
                />
                <Route
                  path="/*"
                  element={
                    <PrivateRoute>
                      <Suspense fallback={fallback}>
                        <Dashboard />
                      </Suspense>
                    </PrivateRoute>
                  }
                />
              </Routes>
            </Router>
          </AlertProvider>
        </TradeProvider>
      </AuthProvider>
    </LocaleProvider>
  );
}

export default App;
