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
