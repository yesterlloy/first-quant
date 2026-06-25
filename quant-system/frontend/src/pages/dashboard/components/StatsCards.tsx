import { useMemo } from 'react';
import { Row, Col, Card, Statistic, Spin } from 'antd';
import {
  DatabaseOutlined,
  CalendarOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';

interface StatsCardsProps {
  overview?: {
    total_stocks?: number;
    total_days?: number;
    total_quotes?: number;
  };
  priceChange?: { pct: number; value: number };
  loading?: boolean;
}

/**
 * 统计卡片组组件
 */
export function StatsCards({ overview, priceChange = { pct: 0, value: 0 }, loading = false }: StatsCardsProps) {
  const statsCards = useMemo(() => [
    {
      title: '股票总数',
      value: overview?.total_stocks || 0,
      suffix: '只',
      icon: <DatabaseOutlined />,
      color: '#1890ff',
    },
    {
      title: '数据覆盖天数',
      value: overview?.total_days || 0,
      suffix: '天',
      icon: <CalendarOutlined />,
      color: '#722ed1',
    },
    {
      title: '行情数据量',
      value: (overview?.total_quotes || 0) / 10000,
      precision: 0,
      suffix: '万条',
      icon: <LineChartOutlined />,
      color: '#fa8c16',
    },
    {
      title: '最新价格变动',
      value: priceChange.pct,
      precision: 2,
      suffix: '%',
      icon: <ThunderboltOutlined />,
      color: priceChange.pct >= 0 ? '#cf1322' : '#3f8600',
    },
  ], [overview, priceChange]);

  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      {statsCards.map((stat, idx) => (
        <Col xs={24} sm={12} lg={6} key={idx}>
          <Card>
            <Spin spinning={loading}>
              <Statistic
                title={stat.title}
                value={stat.value}
                precision={stat.precision ?? 0}
                suffix={stat.suffix}
                valueStyle={{ color: stat.color }}
                prefix={stat.icon}
              />
            </Spin>
          </Card>
        </Col>
      ))}
    </Row>
  );
}
