import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { TradeProvider } from './contexts/TradeContext';
import { AlertProvider } from './contexts/AlertContext';
import { LocaleProvider } from './contexts/LocaleContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import PrivateRoute from './components/PrivateRoute';

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
                <Route path="/login" element={<Login />} />
                <Route
                  path="/*"
                  element={
                    <PrivateRoute>
                      <Dashboard />
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
