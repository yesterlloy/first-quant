import { useQuery } from '@tanstack/react-query';
import { getDataOverview } from '../../../services';

/**
 * 获取数据概览统计的 Hook
 */
export function useOverviewData() {
  const {
    data: overview,
    isLoading: loading,
    refetch,
  } = useQuery({
    queryKey: ['dataOverview'],
    queryFn: () => getDataOverview(),
    staleTime: 5 * 60 * 1000, // 5 分钟缓存
  });

  return {
    overview,
    loading,
    refresh: refetch,
  };
}
