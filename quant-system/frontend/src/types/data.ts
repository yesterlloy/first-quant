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

// ============ 交易相关类型 ============

/** 持仓信息 */
export interface PositionOut {
  id: number;
  date: string;
  code: string;
  shares?: number;
  weight?: number;
  cost_price?: number;
  current_price?: number;
  market_value?: number;
  profit_pct?: number;
  profit_amount?: number;
}

/** 订单信息 */
export interface OrderOut {
  id: number;
  order_id: string;
  date: string;
  code: string;
  action: 'buy' | 'sell';
  shares: number;
  price?: number;
  status: 'pending' | 'filled' | 'canceled' | 'rejected';
  created_at?: string;
  updated_at?: string;
}

/** 成交记录 */
export interface TradeOut {
  id: number;
  trade_id: string;
  order_id?: string;
  date: string;
  code: string;
  action: 'buy' | 'sell';
  shares: number;
  price: number;
  filled_at?: string;
  amount?: number;
}

/** 账户快照 */
export interface AccountSnapshotOut {
  id: number;
  date: string;
  total_value?: number;
  cash?: number;
  market_value?: number;
  return_pct?: number;
  created_at?: string;
}

/** 组合概览 */
export interface PortfolioSummaryOut {
  total_value: number;
  cash: number;
  market_value: number;
  position_count: number;
  today_pnl: number;
  today_return_pct: number;
  total_return_pct: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
}

/** 交易统计 */
export interface TradingStatsOut {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_profit: number;
  avg_profit_per_trade: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
}

// ============ ML 模型相关类型 ============

/** 模型信息 */
export interface MLModelInfo {
  name: string;
  display_name: string;
  description: string;
  type: string;
  supported_params: string[];
}

/** 训练任务 */
export interface MLTrainTask {
  id: number;
  model_name: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  start_date?: string;
  end_date?: string;
  train_start?: string;
  train_end?: string;
  val_start?: string;
  val_end?: string;
  train_samples?: number;
  val_samples?: number;
  train_auc?: number;
  val_auc?: number;
  top_return?: number;
  feature_count?: number;
  params?: Record<string, any>;
  model_path?: string;
  error_message?: string;
  created_at?: string;
  started_at?: string;
  finished_at?: string;
}

/** 因子重要性 */
export interface MLFactorImportance {
  id: number;
  task_id: number;
  feature_name: string;
  importance: number;
  rank?: number;
  created_at?: string;
}

/** 预测信号 */
export interface MLTimingSignal {
  id: number;
  timestamp: string;
  code: string;
  model_name: string;
  signal?: number;
  probability?: number;
  prediction?: 'buy' | 'sell' | 'hold';
}

// ============ 风控相关类型 ============

/** 风控规则 */
export interface RiskRuleOut {
  id: number;
  rule_name: string;
  rule_type: string;
  level: string;
  params?: Record<string, any>;
  enabled: boolean;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

/** 风控事件 */
export interface RiskEventOut {
  id: number;
  timestamp: string;
  level: string;
  type?: string;
  code?: string;
  message?: string;
  details?: Record<string, any>;
  created_at?: string;
}

/** 风控检查结果 */
export interface RiskCheckResult {
  passed: boolean;
  level: string;
  triggered_rules: string[];
  warnings: string[];
  errors: string[];
  details: Record<string, any>;
}

/** 风控统计 */
export interface RiskStatsOut {
  total_events: number;
  today_events: number;
  warning_count: number;
  block_count: number;
  total_rules: number;
  enabled_rules: number;
  top_triggers: Array<{ type: string; count: number }>;
}

// ============ 调度器相关类型 ============

/** 调度任务 */
export interface SchedulerTaskOut {
  id: number;
  task_name: string;
  description?: string;
  cron: string;
  enabled: boolean;
  timeout: number;
  retry: boolean;
  retry_max: number;
  last_run_at?: string;
  next_run_at?: string;
  last_status?: string;
  created_at?: string;
  updated_at?: string;
}

/** 调度日志 */
export interface SchedulerLogOut {
  id: number;
  task_name: string;
  status: string;
  start_time: string;
  end_time?: string;
  duration_seconds?: number;
  retry_count: number;
  error_message?: string;
  created_at?: string;
}

/** 调度器统计 */
export interface SchedulerStatsOut {
  total_tasks: number;
  enabled_tasks: number;
  today_runs: number;
  success_count: number;
  failed_count: number;
  avg_duration: number;
  running_tasks: string[];
  recently_failed: Array<{
    task_name: string;
    error_message?: string;
    failed_at?: string;
  }>;
}
