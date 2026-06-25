import { useState } from 'react';
import { message } from 'antd';
import dayjs from 'dayjs';

import {
  DashboardHeader,
  DataRangeInfo,
  StatsCards,
  KlineChart,
  StockList,
} from './components';
import { useOverviewData, useStockListData, useKlineData } from './hooks';

/**
 * 数据看板：展示系统数据统计 + K 线图 + 股票列表
 */
export default function Dashboard() {
  // ===== 页面状态 =====
  const [selectedStock, setSelectedStock] = useState<string>('000001');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(1, 'year'),
    dayjs(),
  ]);

  // ===== 数据 Hooks =====
  const { overview, loading: loadingOverview, refresh: refreshOverview } = useOverviewData();
  const { stockData, loading: loadingStocks, refresh: refreshStocks } = useStockListData(searchKeyword);
  const { quotes, loading: loadingQuotes, priceChange, refresh: refreshQuotes } = useKlineData(selectedStock, dateRange);

  // ===== 事件处理 =====
  const handleRefresh = () => {
    message.loading('刷新中...', 0.5).then(() => {
      refreshOverview();
      refreshStocks();
      refreshQuotes();
    });
  };

  return (
    <div className="page-container" style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 页面头部 */}
      <DashboardHeader onRefresh={handleRefresh} />

      {/* 数据范围提示 */}
      <DataRangeInfo
        minDate={overview?.min_date}
        maxDate={overview?.max_date}
        lastUpdate={overview?.last_update}
      />

      {/* 关键指标卡片 */}
      <StatsCards
        overview={overview}
        priceChange={priceChange}
        loading={loadingOverview}
      />

      {/* K 线图 */}
      <KlineChart
        selectedStock={selectedStock}
        onStockChange={setSelectedStock}
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
        quotes={quotes}
        loading={loadingQuotes}
      />

      {/* 股票列表 */}
      <StockList
        searchKeyword={searchKeyword}
        onSearchChange={setSearchKeyword}
        stockData={stockData}
        loading={loadingStocks}
        onSelectStock={setSelectedStock}
      />
    </div>
  );
}
