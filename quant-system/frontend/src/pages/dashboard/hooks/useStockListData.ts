import { useQuery } from '@tanstack/react-query';
import { getStockList } from '../../../services';

/**
 * 获取股票列表的 Hook
 */
export function useStockListData(keyword: string) {
  const {
    data: stockData,
    isLoading: loading,
    refetch,
  } = useQuery({
    queryKey: ['stockList', keyword],
    queryFn: () =>
      getStockList({
        page: 1,
        page_size: 100,
        keyword: keyword || undefined,
      }),
    staleTime: 2 * 60 * 1000, // 2 分钟缓存
  });

  return {
    stockData,
    loading,
    refresh: refetch,
  };
}
