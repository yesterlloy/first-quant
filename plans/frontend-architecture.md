# 前端架构设计文档

> **版本**: v1.1
> **更新日期**: 2026-06-23
> **技术栈**: React 18 + TypeScript + Ant Design 6 + Vite

---

## 🎯 设计原则

1. **类型安全**: 全面使用 TypeScript，前后端类型共享
2. **性能优先**: 按需加载、虚拟列表、图表优化
3. **开发体验**: 热更新、类型提示、代码自动补全
4. **可维护性**: 模块化设计，清晰的目录结构
5. **用户体验**: 流畅的交互动画，友好的错误提示

---

## 📦 技术栈详情

| 类别 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 框架 | React | 18.x | Hooks 优先 |
| 语言 | TypeScript | 5.x | 严格模式 |
| UI 框架 | Ant Design | 6.x | ✨ 最新企业级设计系统 |
| 路由 | React Router | 6.x | 嵌套路由 + 懒加载 |
| 状态管理 | Zustand | 4.x | 轻量高效 |
| 数据请求 | Axios | 1.x | 拦截器 + 自动重试 |
| 请求缓存 | React Query | 5.x | SWR 替代方案 |
| 图表 | ECharts | 5.x | 高性能图表 |
| 表单 | React Hook Form | 7.x | 高性能表单 |
| 工具库 | Lodash-es | - | 按需引入 |
| 日期处理 | Day.js | - | 轻量替代 Moment.js |
| 构建工具 | Vite | 5.x | 极速开发体验 |
| 代码规范 | ESLint + Prettier | - | 统一代码风格 |
| CSS 方案 | Tailwind CSS | 3.x | 原子化 CSS |

---

## ✨ Ant Design v6 新特性说明

### 核心升级点

| 特性 | 说明 | 应用场景 |
|------|------|---------|
| **全新 Token System** | v6 设计 token 系统，更灵活的主题定制 | 量化平台主题定制 |
| **CSS-in-JS 性能优化** | 运行时性能提升 50%+ | 复杂表格、图表页面 |
| **组件 v6 升级** | Table/Form/Modal 等核心组件重构 | 全部业务场景 |
| **React 18 原生支持** | 完整支持 Concurrent Features | Suspense、Transitions |
| **更小的包体积** | Tree-shaking 优化，按需加载 | 首屏加载优化 |
| **无障碍增强** | ARIA 标签、键盘导航全面升级 | 合规性要求 |

### v6 组件新特性应用

1. **Table v6** - 虚拟滚动原生支持，10万行数据流畅渲染
   - 股票列表、交易记录、回测历史等大表格场景

2. **Form v6** - 性能优化，表单验证速度提升
   - 回测参数配置、策略参数设置等复杂表单

3. **Flex/Grid 布局组件** - 原生 CSS Grid 支持
   - Dashboard 卡片布局，响应式设计

4. **App 包裹器** - 全局 message/modal/notification 简化调用
   - 统一的消息提示、弹窗管理

---

## 📁 目录结构

```
frontend/
├── public/                          # 静态资源
│   ├── favicon.ico
│   └── index.html
├── src/
│   ├── assets/                      # 资源文件
│   │   ├── images/
│   │   └── styles/
│   │       ├── global.css          # 全局样式
│   │       └── variables.css       # CSS 变量
│   ├── components/                  # 公共组件
│   │   ├── charts/                 # 图表组件
│   │   │   ├── LineChart.tsx      # 折线图（K线、收益曲线）
│   │   │   ├── BarChart.tsx       # 柱状图
│   │   │   ├── PieChart.tsx       # 饼图
│   │   │   ├── CandleChart.tsx    # K线图
│   │   │   └── index.ts
│   │   ├── tables/                 # 表格组件
│   │   │   ├── DataTable.tsx      # 通用数据表格
│   │   │   ├── Pagination.tsx     # 分页
│   │   │   └── index.ts
│   │   ├── layouts/                # 布局组件
│   │   │   ├── MainLayout.tsx     # 主布局（侧边栏 + 头部）
│   │   │   ├── Header.tsx         # 头部
│   │   │   ├── Sidebar.tsx        # 侧边栏
│   │   │   └── index.ts
│   │   ├── common/                 # 通用组件
│   │   │   ├── StatusTag.tsx      # 状态标签
│   │   │   ├── NumberFlow.tsx     # 数字滚动
│   │   │   ├── EmptyState.tsx     # 空状态
│   │   │   ├── Loading.tsx        # 加载状态
│   │   │   └── ErrorBoundary.tsx  # 错误边界
│   │   └── forms/                  # 表单组件
│   │       ├── DateRangePicker.tsx
│   │       ├── StockSelector.tsx
│   │       └── StrategyForm.tsx
│   ├── pages/                       # 页面组件
│   │   ├── dashboard/              # 数据看板
│   │   │   ├── index.tsx
│   │   │   ├── Overview.tsx       # 概览卡片
│   │   │   ├── MarketTrend.tsx    # 市场趋势
│   │   │   └── components/        # 看板子组件
│   │   ├── factor/                 # 因子分析
│   │   │   ├── index.tsx
│   │   │   ├── FactorList.tsx     # 因子列表
│   │   │   ├── FactorDetail.tsx   # 因子详情
│   │   │   ├── ICAnalysis.tsx     # IC分析
│   │   │   └── LayerTest.tsx      # 分层回测
│   │   ├── backtest/               # 策略回测
│   │   │   ├── index.tsx
│   │   │   ├── StrategySelect.tsx # 策略选择
│   │   │   ├── BacktestForm.tsx   # 回测配置
│   │   │   ├── ResultPanel.tsx    # 结果展示
│   │   │   ├── HistoryList.tsx    # 回测历史
│   │   │   └── components/
│   │   │       ├── EquityChart.tsx
│   │   │       ├── MetricsTable.tsx
│   │   │       └── DrawdownChart.tsx
│   │   ├── ml/                     # ML模型
│   │   │   ├── index.tsx
│   │   │   ├── ModelList.tsx
│   │   │   ├── TrainPanel.tsx
│   │   │   ├── SignalDisplay.tsx
│   │   │   └── ProgressBar.tsx
│   │   ├── trading/                # 实盘监控
│   │   │   ├── index.tsx
│   │   │   ├── PositionList.tsx   # 持仓列表
│   │   │   ├── OrderList.tsx      # 订单列表
│   │   │   ├── TradeList.tsx      # 交易记录
│   │   │   └── AssetOverview.tsx  # 资产概览
│   │   ├── risk/                   # 风控中心
│   │   │   ├── index.tsx
│   │   │   ├── EventList.tsx
│   │   │   └── RuleConfig.tsx
│   │   ├── scheduler/              # 任务调度
│   │   │   ├── index.tsx
│   │   │   ├── TaskList.tsx
│   │   │   └── LogViewer.tsx
│   │   ├── settings/               # 系统设置
│   │   │   ├── index.tsx
│   │   │   ├── DataSource.tsx
│   │   │   └── BrokerConfig.tsx
│   │   ├── login/                  # 登录页
│   │   │   └── index.tsx
│   │   └── 404.tsx                # 404页面
│   ├── services/                    # API 服务
│   │   ├── api.ts                 # Axios 实例配置
│   │   ├── types.ts               # API 类型定义
│   │   ├── data.ts                # 数据模块 API
│   │   ├── factor.ts              # 因子模块 API
│   │   ├── backtest.ts            # 回测模块 API
│   │   ├── ml.ts                  # ML 模块 API
│   │   ├── trading.ts             # 交易模块 API
│   │   ├── risk.ts                # 风控模块 API
│   │   └── scheduler.ts           # 调度模块 API
│   ├── stores/                      # 状态管理
│   │   ├── useUserStore.ts        # 用户状态
│   │   ├── useBacktestStore.ts    # 回测状态
│   │   └── useTradingStore.ts     # 交易状态
│   ├── hooks/                       # 自定义 Hooks
│   │   ├── useDebounce.ts         # 防抖
│   │   ├── useThrottle.ts         # 节流
│   │   ├── useWebSocket.ts        # WebSocket
│   │   ├── useECharts.ts          # ECharts 封装
│   │   └── useTable.ts            # 表格逻辑
│   ├── utils/                       # 工具函数
│   │   ├── format.ts              # 格式化（金额、百分比、日期）
│   │   ├── constants.ts           # 常量定义
│   │   ├── validation.ts          # 验证规则
│   │   └── helpers.ts             # 通用工具
│   ├── types/                       # TypeScript 类型
│   │   ├── api.ts                 # API 响应类型
│   │   ├── models.ts              # 业务模型
│   │   └── components.ts          # 组件 Props 类型
│   ├── App.tsx                      # 根组件
│   ├── main.tsx                     # 入口文件
│   └── vite-env.d.ts               # Vite 类型声明
├── tests/                           # 测试文件
│   ├── unit/                       # 单元测试
│   └── e2e/                        # E2E 测试
├── .env                             # 环境变量
├── .env.development                 # 开发环境变量
├── .env.production                  # 生产环境变量
├── .eslintrc.cjs                    # ESLint 配置
├── .prettierrc                      # Prettier 配置
├── tsconfig.json                    # TypeScript 配置
├── vite.config.ts                   # Vite 配置
├── package.json                     # 依赖管理
└── README.md                        # 项目说明
```

---

## 🔄 状态管理设计

### Zustand Store 分层

```typescript
// stores/useUserStore.ts
interface UserState {
  token: string | null
  userInfo: User | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
}

// stores/useBacktestStore.ts
interface BacktestState {
  runningTasks: Map<string, BacktestTask>
  results: Map<string, BacktestResult>
  history: BacktestRecord[]
  submitTask: (params: BacktestParams) => Promise<string>
  pollTaskStatus: (taskId: string) => Promise<void>
  fetchHistory: () => Promise<void>
}

// stores/useTradingStore.ts
interface TradingState {
  positions: Position[]
  orders: Order[]
  assetOverview: AssetOverview | null
  loading: boolean
  fetchPositions: () => Promise<void>
  fetchOrders: () => Promise<void>
  fetchAssetOverview: () => Promise<void>
}
```

---

## 📊 图表组件设计

### ECharts 封装 Hook
```typescript
// hooks/useECharts.ts
export function useECharts(
  containerRef: RefObject<HTMLDivElement>,
  optionGetter: () => EChartsOption,
  deps: any[]
) {
  const chartRef = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    const chart = echarts.init(containerRef.current)
    chartRef.current = chart

    const resizeObserver = new ResizeObserver(() => {
      chart.resize()
    })
    resizeObserver.observe(containerRef.current!)

    return () => {
      resizeObserver.disconnect()
      chart.dispose()
    }
  }, [])

  useEffect(() => {
    chartRef.current?.setOption(optionGetter(), true)
  }, deps)

  return chartRef
}
```

### 常用图表组件

1. **K线图组件**
```typescript
// components/charts/CandleChart.tsx
interface CandleChartProps {
  data: QuoteData[]
  volume?: boolean
  indicators?: string[]
}
```

2. **收益曲线组件**
```typescript
// components/charts/EquityChart.tsx
interface EquityChartProps {
  data: EquityPoint[]
  benchmark?: EquityPoint[]
  showDrawdown?: boolean
}
```

3. **通用折线图组件**
```typescript
// components/charts/LineChart.tsx
interface LineChartProps {
  data: any[]
  xField: string
  yFields: string[]
  colors?: string[]
}
```

---

## 🎨 主题设计

### 色彩系统
```css
/* styles/variables.css */
:root {
  /* 主色调 - 蓝色系 */
  --primary-color: #1890ff;
  --primary-hover: #40a9ff;
  --primary-active: #096dd9;

  /* 成功色 */
  --success-color: #52c41a;
  --success-bg: #f6ffed;

  /* 警告色 */
  --warning-color: #faad14;
  --warning-bg: #fffbe6;

  /* 错误色 */
  --error-color: #ff4d4f;
  --error-bg: #fff2f0;

  /* 中性色 */
  --text-primary: #000000e6;
  --text-secondary: #000000a6;
  --border-color: #d9d9d9;
  --bg-color: #f5f7fa;
}
```

### 盈利/亏损专属色
```css
--profit-color: #ff4d4f;    /* 红涨 */
--loss-color: #52c41a;      /* 绿跌 */
```

---

## 🔌 API 请求设计

### Axios 拦截器
```typescript
// services/api.ts
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
})

// 请求拦截器：添加 Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一处理错误
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Token 过期，退出登录
      useUserStore.getState().logout()
      message.error('登录已过期，请重新登录')
    }
    return Promise.reject(error)
  }
)
```

### React Query 集成
```typescript
// 使用 React Query 管理请求状态
const { data, isLoading, error } = useQuery({
  queryKey: ['stocks', page, keyword],
  queryFn: () => fetchStocks({ page, keyword }),
  staleTime: 5 * 60 * 1000, // 5分钟缓存
})
```

---

## 🔐 路由权限设计

```typescript
// App.tsx
function App() {
  const isAuthenticated = useUserStore(s => s.isAuthenticated)

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<MainLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="factor" element={<FactorPage />} />
            <Route path="backtest" element={<BacktestPage />} />
            <Route path="ml" element={<MLPage />} />
            <Route path="trading" element={<TradingPage />} />
            <Route path="risk" element={<RiskPage />} />
            <Route path="scheduler" element={<SchedulerPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  )
}
```

---

## ⚡ 性能优化策略

### 1. 代码分割
```typescript
// 路由懒加载
const DashboardPage = lazy(() => import('./pages/dashboard'))
const FactorPage = lazy(() => import('./pages/factor'))
```

### 2. 虚拟列表
- 长表格使用 `@tanstack/react-virtual`
- 1000+ 条数据启用虚拟滚动

### 3. 图表优化
- ECharts 按需引入模块
- 大数据量启用降采样
- WebGL 渲染加速

### 4. 请求优化
- React Query 缓存去重
- 轮询数据间隔优化
- 批量请求合并

---

## 📱 响应式设计

| 断点 | 设备 | 布局 |
|------|------|------|
| < 768px | 手机 | 单栏布局，侧边栏折叠 |
| 768px ~ 1200px | 平板 | 侧边栏可折叠 |
| > 1200px | 桌面 | 完整侧边栏 + 内容区 |

---

## 🔧 开发配置

### Vite 配置要点（Ant Design v6 优化）
```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react(),
    // Ant Design v6 原生支持 ESM tree-shaking，无需额外插件
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  // Ant Design v6 CSS-in-JS 优化
  css: {
    preprocessorOptions: {
      less: {
        modifyVars: {
          // 自定义主题 Token
          '@primary-color': '#1890ff',
        },
        javascriptEnabled: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'antd-vendor': ['antd', '@ant-design/icons-v6'],
          'charts': ['echarts'],
        },
      },
    },
  },
})
```

### Ant Design v6 主题配置
```typescript
// theme/index.ts
import { ThemeConfig } from 'antd'

export const quantTheme: ThemeConfig = {
  token: {
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    // 量化平台专属色彩
    colorProfit: '#ff4d4f',     // 红涨
    colorLoss: '#52c41a',       // 绿跌
    borderRadius: 6,
  },
  components: {
    Table: {
      headerBg: '#fafafa',
      borderColor: '#f0f0f0',
      rowHoverBg: '#e6f7ff',
    },
    Card: {
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    },
  },
}
```

---

## ✅ 质量保障

### 代码规范
- ESLint: Airbnb 规则 + TypeScript 插件
- Prettier: 统一代码格式化
- Husky + lint-staged: 提交前检查

### 测试策略
- 单元测试: Vitest + React Testing Library
- 组件测试: 关键组件快照测试
- E2E 测试: Playwright 核心流程

---

## 🚀 部署策略

### 构建产物优化
- 生成 SourceMap（生产环境可选）
- gzip 压缩
- CDN 加速静态资源

### Docker 部署
```dockerfile
# 构建阶段
FROM node:20-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# 运行阶段
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```
