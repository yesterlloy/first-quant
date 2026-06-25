import { useState } from 'react';
import {
  Card,
  Col,
  Row,
  Statistic,
  Typography,
  Table,
  Select,
  Tabs,
  Spin,
  Tag,
  Button,
  Space,
  message,
} from 'antd';
import {
  BarChartOutlined,
  FallOutlined,
  RiseOutlined,
  ThunderboltOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';

import { getFactorList, getFactorValues, getFactorICAnalysis } from '../../services';
import type { FactorInfo, FactorValue } from '../../types/data';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

/**
 * 因子分析页面
 */
export default function FactorAnalysis() {
  const [selectedFactor, setSelectedFactor] = useState<string>('VOL_20');
  const [activeTab, setActiveTab] = useState<string>('list');

  // ===== 因子列表 =====
  const {
    data: factorData,
    isLoading: loadingFactors,
    refetch: refetchFactors,
  } = useQuery({
    queryKey: ['factorList'],
    queryFn: () => getFactorList({ page: 1, page_size: 50 }),
    staleTime: 5 * 60 * 1000,
  });

  // ===== 因子值 =====
  const {
    data: valueData,
    isLoading: loadingValues,
    refetch: refetchValues,
  } = useQuery({
    queryKey: ['factorValues', selectedFactor],
    queryFn: () =>
      getFactorValues({
        factor_name: selectedFactor,
        page: 1,
        page_size: 100,
      }),
    staleTime: 2 * 60 * 1000,
    enabled: !!selectedFactor,
  });

  // ===== IC 分析 =====
  const {
    data: icAnalysis,
    isLoading: loadingIC,
    refetch: refetchIC,
  } = useQuery({
    queryKey: ['factorIC', selectedFactor],
    queryFn: () => getFactorICAnalysis({ factor_name: selectedFactor }),
    staleTime: 5 * 60 * 1000,
    enabled: !!selectedFactor,
  });

  // 刷新
  const handleRefresh = () => {
    message.loading('刷新中...', 0.5).then(() => {
      refetchFactors();
      refetchValues();
      refetchIC();
    });
  };

  // 因子分类颜色
  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      volatility: 'orange',
      momentum: 'red',
      reversal: 'cyan',
      quality: 'purple',
      value: 'green',
      growth: 'blue',
      technical: 'geekblue',
    };
    return colors[category.toLowerCase()] || 'default';
  };

  // 因子统计卡片
  const statsCards = [
    {
      title: '因子总数',
      value: factorData?.total || 0,
      icon: <BarChartOutlined />,
      color: '#1890ff',
    },
    {
      title: 'IC均值',
      value: (icAnalysis?.ic_mean || 0) * 100,
      precision: 2,
      suffix: '%',
      icon: <ThunderboltOutlined />,
      color: (icAnalysis?.ic_mean || 0) >= 0 ? '#cf1322' : '#3f8600',
    },
    {
      title: 'ICIR',
      value: icAnalysis?.ir || 0,
      precision: 2,
      icon: <RiseOutlined />,
      color: (icAnalysis?.ir || 0) >= 0.5 ? '#52c41a' : '#fa8c16',
    },
    {
      title: 'IC胜率',
      value: (icAnalysis?.win_rate || 0) * 100,
      precision: 1,
      suffix: '%',
      icon: <FallOutlined />,
      color: (icAnalysis?.win_rate || 0) >= 0.55 ? '#52c41a' : '#fa8c16',
    },
  ];

  // 因子列表列
  const factorColumns = [
    {
      title: '因子名称',
      dataIndex: 'display_name',
      key: 'display_name',
      width: 150,
      render: (name: string, record: FactorInfo) => (
        <Space>
          <Text strong>{name}</Text>
          <Tag color={getCategoryColor(record.category)}>{record.category}</Tag>
        </Space>
      ),
    },
    {
      title: '因子代码',
      dataIndex: 'name',
      key: 'name',
      width: 120,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 80,
      render: (d: number) => (
        <Tag color={d > 0 ? 'red' : 'green'}>{d > 0 ? '↑ 正向' : '↓ 负向'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: FactorInfo) => (
        <Button
          type="link"
          size="small"
          onClick={() => {
            setSelectedFactor(record.name);
            setActiveTab('detail');
          }}
        >
          详情
        </Button>
      ),
    },
  ];

  // 因子值分布直方图
  const histogramOption: EChartsOption = {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', name: '因子值区间' },
    yAxis: { type: 'value', name: '股票数量' },
    series: [
      {
        type: 'bar',
        data: (valueData?.items || []).map((v) => v.raw_value.toFixed(4)),
        itemStyle: { color: '#1890ff' },
      },
    ],
  };

  // IC 时序图
  const icSeriesOption: EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['IC 值'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: (icAnalysis?.ic_series || []).map((i) => i.date),
    },
    yAxis: { type: 'value', name: 'IC 值' },
    series: [
      {
        name: 'IC 值',
        type: 'line',
        smooth: true,
        data: (icAnalysis?.ic_series || []).map((i) => i.ic.toFixed(4)),
        markLine: {
          data: [{ type: 'average', name: '均值' }],
          lineStyle: { color: '#cf1322' },
        },
        areaStyle: { color: 'rgba(24, 144, 255, 0.2)' },
      },
    ],
  };

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Title level={3} style={{ margin: 0 }}>
          🧪 因子分析
        </Title>
        <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
          刷新
        </Button>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {statsCards.map((stat, idx) => (
          <Col xs={24} sm={12} lg={6} key={idx}>
            <Card>
              <Spin spinning={loadingFactors || loadingIC}>
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

      {/* Tab 内容区 */}
      <Tabs activeKey={activeTab} onChange={setActiveTab} type="card">
        <TabPane tab="📋 因子列表" key="list">
          <Card>
            <Spin spinning={loadingFactors}>
              <Table
                columns={factorColumns}
                dataSource={factorData?.items || []}
                rowKey="name"
                pagination={{
                  total: factorData?.total || 0,
                  pageSize: factorData?.page_size || 20,
                  current: factorData?.page || 1,
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 个因子`,
                }}
              />
            </Spin>
          </Card>
        </TabPane>

        <TabPane tab="📊 因子详情" key="detail">
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card
                title={`因子值分布 - ${selectedFactor}`}
                extra={
                  <Select
                    style={{ width: 150 }}
                    value={selectedFactor}
                    onChange={setSelectedFactor}
                    options={(factorData?.items || []).map((f) => ({
                      value: f.name,
                      label: f.display_name,
                    }))}
                  />
                }
              >
                <Spin spinning={loadingValues}>
                  <ReactECharts option={histogramOption} style={{ height: 300 }} />
                </Spin>
              </Card>
            </Col>

            <Col span={12}>
              <Card title="IC 时间序列">
                <Spin spinning={loadingIC}>
                  <ReactECharts option={icSeriesOption} style={{ height: 300 }} />
                </Spin>
              </Card>
            </Col>
          </Row>

          {/* 因子值表格 */}
          <Card title="因子值明细" style={{ marginTop: 16 }}>
            <Spin spinning={loadingValues}>
              <Table
                columns={[
                  { title: '股票代码', dataIndex: 'code', key: 'code', width: 100 },
                  { title: '日期', dataIndex: 'date', key: 'date', width: 120 },
                  {
                    title: '原始因子值',
                    dataIndex: 'raw_value',
                    key: 'raw_value',
                    width: 150,
                    render: (v: number) => v?.toFixed(6),
                  },
                  {
                    title: '中性化值',
                    dataIndex: 'neut_value',
                    key: 'neut_value',
                    width: 150,
                    render: (v: number) => (v ? v.toFixed(6) : '-'),
                  },
                ]}
                dataSource={valueData?.items || []}
                rowKey={(record: FactorValue) => `${record.code}-${record.date}`}
                pagination={{
                  total: valueData?.total || 0,
                  pageSize: 20,
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条`,
                }}
              />
            </Spin>
          </Card>
        </TabPane>

        <TabPane tab="📈 IC 热力图" key="heatmap">
          <Card title="因子 IC 相关性热力图">
            <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
              开发中... 敬请期待
            </div>
          </Card>
        </TabPane>

        <TabPane tab="🎯 分层回测" key="layer">
          <Card title="因子分层回测结果">
            <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
              开发中... 敬请期待
            </div>
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
}
