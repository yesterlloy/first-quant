import { Navigate, Route, Routes } from 'react-router-dom';
import type { ReactNode } from 'react';
import MainLayout from './components/layouts/MainLayout';
import Login from './pages/login';
import Dashboard from './pages/dashboard';
import FactorAnalysis from './pages/factor';
import StrategyBacktest from './pages/backtest';
import MLModels from './pages/ml';
import TradingDashboard from './pages/trading';
import { useUserStore } from './stores/useUserStore';

/**
 * 路由守卫：未登录（无 token）时重定向到登录页。
 */
function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = useUserStore((s) => s.token);
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

/**
 * 占位页：尚未实现的模块统一展示「开发中」。
 */
function ComingSoon({ title }: { title: string }) {
  return (
    <div className="page-container">
      <div style={{ textAlign: 'center', padding: '80px 0', color: '#999' }}>
        <h2>{title}</h2>
        <p>该模块开发中，敬请期待 🚧</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      {/* 公开路由 */}
      <Route path="/login" element={<Login />} />

      {/* 受保护路由：统一使用 MainLayout 布局 */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="factor" element={<FactorAnalysis />} />
        <Route path="backtest" element={<StrategyBacktest />} />
        <Route path="ml" element={<MLModels />} />
        <Route path="trading" element={<TradingDashboard />} />
        <Route path="risk" element={<ComingSoon title="风控中心" />} />
        <Route path="scheduler" element={<ComingSoon title="任务调度" />} />
      </Route>

      {/* 兜底：未知路径回到首页 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
