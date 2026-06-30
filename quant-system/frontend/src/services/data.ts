/** 数据模块 API 服务 */

import { http } from './api';
import type {
  StockInfo,
  DailyQuote,
  DataOverview,
  FactorInfo,
  FactorValue,
  ICAnalysis,
  LayerBacktest,
  StrategyInfo,
  BacktestTask,
  BacktestResult,
  PaginatedResponse,
  MLModelInfo,
  MLTrainTask,
  MLFactorImportance,
  MLTimingSignal,
  SchedulerTaskOut,
  SchedulerLogOut,
  SchedulerStatsOut,
} from '../types/data';

/**
 * 获取数据概览统计
 */
export function getDataOverview(): Promise<DataOverview> {
  return http.get<DataOverview>('/data/overview');
}

/**
 * 获取股票列表
 */
export function getStockList(params?: {
  page?: number;
  page_size?: number;
  keyword?: string;
  industry?: string;
}): Promise<PaginatedResponse<StockInfo>> {
  return http.get<PaginatedResponse<StockInfo>>('/data/stocks', { params });
}

/**
 * 获取单只股票详情
 */
export function getStockDetail(code: string): Promise<StockInfo> {
  return http.get<StockInfo>(`/data/stocks/${code}`);
}

/**
 * 获取股票日线行情
 */
export async function getDailyQuotes(params: {
  code: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
}): Promise<DailyQuote[]> {
  const response = await http.get<{ code: string; items: DailyQuote[] }>('/data/quotes', { params });
  return response.items || [];
}

// ============= 因子相关 =============

/**
 * 获取因子列表
 */
export function getFactorList(params?: {
  page?: number;
  page_size?: number;
  category?: string;
}): Promise<PaginatedResponse<FactorInfo>> {
  return http.get<PaginatedResponse<FactorInfo>>('/factor/list', { params });
}

/**
 * 获取因子详情
 */
export function getFactorDetail(name: string): Promise<FactorInfo> {
  return http.get<FactorInfo>(`/factor/${name}`);
}

/**
 * 获取因子值
 */
export function getFactorValues(params: {
  factor_name: string;
  date?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<FactorValue>> {
  return http.get<PaginatedResponse<FactorValue>>('/factor/values', { params });
}

/**
 * 获取 IC 分析结果
 */
export function getFactorICAnalysis(params: {
  factor_name: string;
  start_date?: string;
  end_date?: string;
}): Promise<ICAnalysis> {
  return http.get<ICAnalysis>('/factor/ic-analysis', { params });
}

/**
 * 获取分层回测结果
 */
export function getFactorLayerBacktest(params: {
  factor_name: string;
  start_date?: string;
  end_date?: string;
}): Promise<LayerBacktest[]> {
  return http.get<LayerBacktest[]>('/factor/layer-backtest', { params });
}

// ============= 回测相关 =============

/**
 * 获取策略列表
 */
export function getStrategyList(): Promise<StrategyInfo[]> {
  return http.get<StrategyInfo[]>('/backtest/strategies');
}

/**
 * 提交回测任务
 */
export function submitBacktest(params: {
  strategy_id: string;
  stock_code: string;
  start_date: string;
  end_date: string;
  params?: Record<string, number | string>;
  initial_capital?: number;
  commission?: number;
  slippage?: number;
}): Promise<BacktestTask> {
  return http.post<BacktestTask>('/backtest/run', params);
}

/**
 * 查询回测任务状态
 */
export function getBacktestTask(taskId: string): Promise<BacktestTask> {
  return http.get<BacktestTask>(`/backtest/tasks/${taskId}`);
}

/**
 * 获取回测结果
 */
export function getBacktestResult(taskId: string): Promise<BacktestResult> {
  return http.get<BacktestResult>(`/backtest/result/${taskId}`);
}

/**
 * 获取回测历史
 */
export function getBacktestHistory(params?: {
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<BacktestTask>> {
  return http.get<PaginatedResponse<BacktestTask>>('/backtest/history', { params });
}

// ============= 数据导出 =============

/**
 * 导出 K 线数据为 CSV
 */
export function exportKlineData(code: string, startDate: string, endDate: string) {
  const params = new URLSearchParams({
    code,
    start_date: startDate,
    end_date: endDate,
  });
  window.open(`/api/v1/data/export/kline?${params}`, '_blank');
}

// ============= 交易相关 =============

/**
 * 获取当前持仓
 */
export function getPositions(date?: string): Promise<PositionOut[]> {
  return http.get<PositionOut[]>('/trading/positions', { params: { date } });
}

/**
 * 获取订单列表
 */
export function getOrders(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  code?: string;
  start_date?: string;
  end_date?: string;
}): Promise<PaginatedResponse<OrderOut>> {
  return http.get<PaginatedResponse<OrderOut>>('/trading/orders', { params });
}

/**
 * 获取订单详情
 */
export function getOrderDetail(orderId: number): Promise<OrderOut> {
  return http.get<OrderOut>(`/trading/orders/${orderId}`);
}

/**
 * 创建订单
 */
export function createOrder(code: string, action: string, shares: number, price?: number): Promise<OrderOut> {
  return http.post<OrderOut>('/trading/orders', { code, action, shares, price });
}

/**
 * 取消订单
 */
export function cancelOrder(orderId: number): Promise<OrderOut> {
  return http.post<OrderOut>(`/trading/orders/${orderId}/cancel`);
}

/**
 * 获取成交记录
 */
export function getTrades(params?: {
  page?: number;
  page_size?: number;
  code?: string;
  start_date?: string;
  end_date?: string;
}): Promise<PaginatedResponse<TradeOut>> {
  return http.get<PaginatedResponse<TradeOut>>('/trading/trades', { params });
}

/**
 * 获取账户快照
 */
export function getAccountSnapshots(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}): Promise<AccountSnapshotOut[]> {
  return http.get<AccountSnapshotOut[]>('/trading/account/snapshots', { params });
}

/**
 * 获取组合概览
 */
export function getPortfolioSummary(): Promise<PortfolioSummaryOut> {
  return http.get<PortfolioSummaryOut>('/trading/portfolio/summary');
}

/**
 * 获取交易统计
 */
export function getTradingStats(params?: {}): Promise<TradingStatsOut> {
  return http.get<TradingStatsOut>('/trading/stats', { params });
}

// ============= 风控相关 =============

/**
 * 获取风控规则列表
 */
export function getRiskRules(params?: {
  page?: number;
  page_size?: number;
  level?: string;
  enabled?: boolean;
}): Promise<PaginatedResponse<RiskRuleOut>> {
  return http.get<PaginatedResponse<RiskRuleOut>>('/risk/rules', { params });
}

/**
 * 获取单个风控规则
 */
export function getRiskRule(ruleId: number): Promise<RiskRuleOut> {
  return http.get<RiskRuleOut>(`/risk/rules/${ruleId}`);
}

/**
 * 创建风控规则
 */
export function createRiskRule(data: {
  rule_name: string;
  rule_type: string;
  level: string;
  params?: Record<string, any>;
  enabled?: boolean;
  description?: string;
}): Promise<RiskRuleOut> {
  return http.post<RiskRuleOut>('/risk/rules', data);
}

/**
 * 更新风控规则
 */
export function updateRiskRule(ruleId: number, data: Partial<{
  rule_name: string;
  rule_type: string;
  level: string;
  params?: Record<string, any>;
  enabled?: boolean;
  description?: string;
}>): Promise<RiskRuleOut> {
  return http.put<RiskRuleOut>(`/risk/rules/${ruleId}`, data);
}

/**
 * 删除风控规则
 */
export function deleteRiskRule(ruleId: number): Promise<void> {
  return http.delete<void>(`/risk/rules/${ruleId}`);
}

/**
 * 启用/禁用风控规则
 */
export function toggleRiskRule(ruleId: number, enabled: boolean): Promise<RiskRuleOut> {
  return http.post<RiskRuleOut>(`/risk/rules/${ruleId}/toggle`, {}, { params: { enabled } });
}

/**
 * 获取风控事件列表
 */
export function getRiskEvents(params?: {
  page?: number;
  page_size?: number;
  level?: string;
  event_type?: string;
  code?: string;
  start_date?: string;
  end_date?: string;
}): Promise<PaginatedResponse<RiskEventOut>> {
  return http.get<PaginatedResponse<RiskEventOut>>('/risk/events', { params });
}

/**
 * 获取单个风控事件
 */
export function getRiskEvent(eventId: number): Promise<RiskEventOut> {
  return http.get<RiskEventOut>(`/risk/events/${eventId}`);
}

/**
 * 执行风控检查
 */
export function checkRisk(data: {
  action: string;
  code?: string;
  shares?: number;
  price?: number;
}): Promise<RiskCheckResult> {
  return http.post<RiskCheckResult>('/risk/check', data);
}

/**
 * 获取风控统计
 */
export function getRiskStats(): Promise<RiskStatsOut> {
  return http.get<RiskStatsOut>('/risk/stats');
}

// ============= ML 模型相关 =============

/**
 * 获取支持的模型列表
 */
export function getMLModelList(): Promise<MLModelInfo[]> {
  return http.get<MLModelInfo[]>('/ml/models');
}

/**
 * 获取训练任务列表
 */
export function getMLTrainTaskList(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  model_name?: string;
}): Promise<PaginatedResponse<MLTrainTask>> {
  return http.get<PaginatedResponse<MLTrainTask>>('/ml/tasks', { params });
}

/**
 * 获取训练任务详情
 */
export function getMLTrainTask(taskId: number): Promise<MLTrainTask> {
  return http.get<MLTrainTask>(`/ml/tasks/${taskId}`);
}

/**
 * 提交训练任务
 */
export function submitMLTrainTask(params: {
  model_name: string;
  start_date?: string;
  end_date?: string;
  factors?: string[];
  params?: Record<string, any>;
}): Promise<MLTrainTask> {
  return http.post<MLTrainTask>('/ml/train', params);
}

/**
 * 执行训练任务
 */
export function runMLTrainTask(taskId: number): Promise<MLTrainTask> {
  return http.post<MLTrainTask>(`/ml/tasks/${taskId}/run`);
}

/**
 * 删除训练任务
 */
export function deleteMLTrainTask(taskId: number): Promise<void> {
  return http.delete<void>(`/ml/tasks/${taskId}`);
}

/**
 * 获取因子重要性
 */
export function getMLFactorImportance(params?: {
  task_id?: number;
  model_name?: string;
  top_n?: number;
}): Promise<MLFactorImportance[]> {
  return http.get<MLFactorImportance[]>('/ml/factor-importance', { params });
}

/**
 * 获取预测信号
 */
export function getMLSignals(params?: {
  page?: number;
  page_size?: number;
  date?: string;
  code?: string;
  model_name?: string;
}): Promise<PaginatedResponse<MLTimingSignal>> {
  return http.get<PaginatedResponse<MLTimingSignal>>('/ml/signals', { params });
}

// ============= 调度器相关 =============

/**
 * 获取调度器统计
 */
export function getSchedulerStats(): Promise<SchedulerStatsOut> {
  return http.get<SchedulerStatsOut>('/scheduler/stats');
}

/**
 * 获取任务列表
 */
export function getSchedulerTasks(params?: {
  enabled?: boolean;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<SchedulerTaskOut>> {
  return http.get<PaginatedResponse<SchedulerTaskOut>>('/scheduler/tasks', { params });
}

/**
 * 获取任务详情
 */
export function getSchedulerTask(taskId: number): Promise<SchedulerTaskOut> {
  return http.get<SchedulerTaskOut>(`/scheduler/tasks/${taskId}`);
}

/**
 * 创建任务
 */
export function createSchedulerTask(data: {
  task_name: string;
  description?: string;
  cron: string;
  enabled?: boolean;
  timeout?: number;
  retry?: boolean;
  retry_max?: number;
}): Promise<SchedulerTaskOut> {
  return http.post<SchedulerTaskOut>('/scheduler/tasks', data);
}

/**
 * 更新任务
 */
export function updateSchedulerTask(taskId: number, data: Partial<{
  task_name: string;
  description?: string;
  cron: string;
  enabled?: boolean;
  timeout?: number;
  retry?: boolean;
  retry_max?: number;
}>): Promise<SchedulerTaskOut> {
  return http.put<SchedulerTaskOut>(`/scheduler/tasks/${taskId}`, data);
}

/**
 * 删除任务
 */
export function deleteSchedulerTask(taskId: number): Promise<void> {
  return http.delete<void>(`/scheduler/tasks/${taskId}`);
}

/**
 * 启用/禁用任务
 */
export function toggleSchedulerTask(taskId: number, enabled: boolean): Promise<SchedulerTaskOut> {
  return http.post<SchedulerTaskOut>(`/scheduler/tasks/${taskId}/toggle`, {}, { params: { enabled } });
}

/**
 * 手动触发任务
 */
export function triggerSchedulerTask(taskName: string): Promise<{
  task_name: string;
  triggered: boolean;
  log_id: number;
  message: string;
}> {
  return http.post(`/scheduler/tasks/${taskName}/trigger`);
}

/**
 * 初始化默认任务
 */
export function initDefaultTasks(): Promise<{ initialized: boolean }> {
  return http.post('/scheduler/init');
}

/**
 * 获取执行日志列表
 */
export function getSchedulerLogs(params?: {
  task_name?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<SchedulerLogOut>> {
  return http.get<PaginatedResponse<SchedulerLogOut>>('/scheduler/logs', { params });
}

/**
 * 获取日志详情
 */
export function getSchedulerLog(logId: number): Promise<SchedulerLogOut> {
  return http.get<SchedulerLogOut>(`/scheduler/logs/${logId}`);
}
