import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { getDailyQuotes } from '../../../services';

/**
 * 获取 K 线数据的 Hook
 */
export function useKlineData(stockCode: string, dateRange: [dayjs.Dayjs, dayjs.Dayjs]) {
  const {
    data: quotes,
    isLoading: loading,
    refetch,
  } = useQuery({
    queryKey: ['quotes', stockCode, dateRange[0].format('YYYY-MM-DD'), dateRange[1].format('YYYY-MM-DD')],
    queryFn: () =>
      getDailyQuotes({
        code: stockCode,
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD'),
        limit: 500,
      }),
    staleTime: 2 * 60 * 1000, // 2 分钟缓存
  });

  // 计算涨跌幅
  const priceChange = useMemo(() => {
    if (!quotes || quotes.length < 2) return { pct: 0, value: 0 };
    // 注意：后端返回的数据是按 date 倒序排列的，索引 0 是最新的
    const latest = quotes[0];
    const prev = quotes[1];
    if (!latest || !prev) return { pct: 0, value: 0 };
    const pct = ((latest.close - prev.close) / prev.close) * 100;
    return { pct, value: latest.close - prev.close };
  }, [quotes]);

  return {
    quotes,
    loading,
    priceChange,
    refresh: refetch,
  };
}
