/** 数据模块类型定义 */

/** 股票基本信息 */
export interface StockInfo {
  code: string;
  name: string;
  industry?: string;
  list_date?: string;
  delist_date?: string | null;
  market?: string;
}

/** 日线行情 */
export interface DailyQuote {
  code: string;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  turnover: number;
  change_pct?: number;
  turnover_rate?: number;
}

/** K 线数据点 */
export interface KlinePoint {
  date: string;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
  turnover?: number;
}

/** 指数行情 */
export interface IndexQuote {
  code: string;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  turnover: number;
}

/** 数据概览统计 */
export interface DataOverview {
  total_stocks: number;
  total_days: number;
  min_date: string;
  max_date: string;
  total_quotes: number;
  last_update?: string;
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/** 因子信息 */
export interface FactorInfo {
  name: string;
  display_name: string;
  category: string;
  description: string;
  direction: number;
  formula?: string;
}

/** 因子值 */
export interface FactorValue {
  code: string;
  date: string;
  factor_name: string;
  raw_value: number;
  neut_value?: number;
}

/** IC 分析结果 */
export interface ICAnalysis {
  factor_name: string;
  ic_mean: number;
  ic_std: number;
  ir: number;
  win_rate: number;
  ic_series?: Array<{ date: string; ic: number }>;
}

/** 分层回测结果 */
export interface LayerBacktest {
  factor_name: string;
  layer: number;
  total_return: number;
  annual_return: number;
  sharpe: number;
  max_drawdown: number;
  win_rate: number;
}

/** 策略信息 */
export interface StrategyInfo {
  id: string;
  name: string;
  description: string;
  params: Array<{
    name: string;
    type: string;
    default: number | string;
    min?: number;
    max?: number;
  }>;
}

/** 回测任务 */
export interface BacktestTask {
  task_id: string;
  strategy_id: string;
  stock_code: string;
  start_date: string;
  end_date: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

/** 回测结果指标 */
export interface BacktestMetrics {
  total_return: number;
  annual_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  profit_loss_ratio: number;
  total_trades: number;
}

/** 回测完整结果 */
export interface BacktestResult {
  task_id: string;
  strategy_name: string;
  stock_code: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  metrics: BacktestMetrics;
  equity_curve: Array<{ date: string; value: number }>;
  drawdown_curve: Array<{ date: string; value: number }>;
  trades: Array<{
    date: string;
    side: 'buy' | 'sell';
    price: number;
    quantity: number;
    amount: number;
  }>;
}
