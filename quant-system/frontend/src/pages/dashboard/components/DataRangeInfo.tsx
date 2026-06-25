import { Card, Typography } from 'antd';

const { Text } = Typography;

interface DataRangeInfoProps {
  minDate?: string;
  maxDate?: string;
  lastUpdate?: string;
}

/**
 * 数据范围提示组件
 */
export function DataRangeInfo({ minDate, maxDate, lastUpdate }: DataRangeInfoProps) {
  if (!minDate || !maxDate) return null;

  return (
    <Card style={{ marginBottom: 16 }}>
      <Text type="secondary">
        📅 数据范围：{minDate} ~ {maxDate}
        {lastUpdate && ` | 最后更新：${lastUpdate}`}
      </Text>
    </Card>
  );
}
