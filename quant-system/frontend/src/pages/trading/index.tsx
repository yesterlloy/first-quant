import { useState } from 'react';
import {
  Card,
  Col,
  Row,
  Statistic,
  Typography,
  Table,
  Tag,
  Button,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  DatePicker,
  message,
  Tabs,
  Descriptions,
} from 'antd';
import {
  DollarCircleOutlined,
  ShoppingCartOutlined,
  RiseOutlined,
  FallOutlined,
  PlusOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import dayjs from 'dayjs';

import {
  getPositions,
  getOrders,
  getTrades,
  getPortfolioSummary,
  getTradingStats,
  createOrder,
} from '../../services';
import type { PositionOut, OrderOut, TradeOut, PortfolioSummaryOut, TradingStatsOut } from '../../types/data';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;

/**
 * 实盘监控页面
 */
export default function TradingDashboard() {
  const [activeTab, setActiveTab] = useState<string>('positions');
  const [orderModalVisible, setOrderModalVisible] = useState(false);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // ===== 组合概览 =====
  const { data: summary, isLoading: loadingSummary, refetch: refetchSummary } = useQuery({
    queryKey: ['portfolioSummary'],
    queryFn: () => getPortfolioSummary(),
    staleTime: 5 * 1000,
  });

  // ===== 持仓列表 =====
  const { data: positions, isLoading: loadingPositions, refetch: refetchPositions } = useQuery({
    queryKey: ['positions'],
    queryFn: () => getPositions(),
    staleTime: 5 * 1000,
  });

  // ===== 订单列表 =====
  const { data: orders, isLoading: loadingOrders, refetch: refetchOrders } = useQuery({
    queryKey: ['orders'],
    queryFn: () => getOrders({ page_size: 50 }),
    staleTime: 5 * 1000,
  });

  // ===== 成交记录 =====
  const { data: trades, isLoading: loadingTrades, refetch: refetchTrades } = useQuery({
    queryKey: ['trades'],
    queryFn: () => getTrades({ page_size: 50 }),
    staleTime: 5 * 1000,
  });

  // ===== 交易统计 =====
  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ['tradingStats'],
    queryFn: () => getTradingStats(),
    staleTime: 30 * 1000,
  });

  // ===== 提交订单 Mutation =====
  const orderMutation = useMutation({
    mutationFn: (values: { code: string; action: string; shares: number; price?: number }) =>
      createOrder(values.code, values.action, values.shares, values.price),
    onSuccess: () => {
      message.success('订单提交成功！');
      setOrderModalVisible(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['portfolioSummary'] });
    },
    onError: (error: any) => {
      message.error(error.message || '订单提交失败');
    },
  });

  // ===== 刷新 =====
  const handleRefresh = () => {
    message.loading('刷新中...', 0.5).then(() => {
      refetchSummary();
      refetchPositions();
      refetchOrders();
      refetchTrades();
    });
  };

  // ===== 净值曲线图表 =====
  const equityChart: EChartsOption = {
    tooltip: {
      trigger: 'axis',
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['06-01', '06-02', '06-03', '06-04', '06-05', '06-06', '06-07', '06-08'],
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        name: '净值',
        type: 'line',
        smooth: true,
        data: [1000000, 1002350, 1001800, 1005200, 1003800, 1007500, 1006200, summary?.total_value || 1000000],
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
              { offset: 1, color: 'rgba(24, 144, 255, 0.05)' },
            ],
          },
        },
      },
    ],
  };

  // ===== 收益分布图表 =====
  const returnChart: EChartsOption = {
    tooltip: {
      trigger: 'item',
    },
    legend: {
      bottom: 0,
      left: 'center',
    },
    series: [
      {
        name: '收益分布',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold' },
        },
        data: [
          { value: 35, name: '盈利个股', itemStyle: { color: '#52c41a' } },
          { value: 15, name: '持平个股', itemStyle: { color: '#faad14' } },
          { value: 10, name: '亏损个股', itemStyle: { color: '#ff4d4f' } },
        ],
      },
    ],
  };

  // ===== 持仓表格列 =====
  const positionColumns = [
    {
      title: '股票代码',
      dataIndex: 'code',
      key: 'code',
      width: 120,
      render: (code: string) => <Text strong>{code}</Text>,
    },
    {
      title: '持仓股数',
      dataIndex: 'shares',
      key: 'shares',
      width: 120,
      render: (shares: number) => shares?.toLocaleString(),
    },
    {
      title: '成本价',
      dataIndex: 'cost_price',
      key: 'cost_price',
      width: 120,
      render: (price: number) => price?.toFixed(2),
    },
    {
      title: '最新价',
      dataIndex: 'current_price',
      key: 'current_price',
      width: 120,
      render: (price: number) => price?.toFixed(2),
    },
    {
      title: '市值',
      dataIndex: 'market_value',
      key: 'market_value',
      width: 140,
      render: (value: number) => value?.toLocaleString(),
    },
    {
      title: '持仓收益',
      key: 'profit',
      width: 140,
      render: (_: any, record: PositionOut) => {
        const profit = ((record.current_price || 0) - (record.cost_price || 0)) * (record.shares || 0);
        const profitPct = record.cost_price
          ? ((record.current_price || 0) - record.cost_price) / record.cost_price * 100
          : 0;
        return (
          <div>
            <div style={{ color: profit >= 0 ? '#52c41a' : '#ff4d4f' }}>
              {profit >= 0 ? '+' : ''}{profit.toFixed(2)}
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {profit >= 0 ? '+' : ''}{profitPct.toFixed(2)}%
            </Text>
          </div>
        );
      },
    },
  ];

  // ===== 订单表格列 =====
  const orderColumns = [
    {
      title: '订单ID',
      dataIndex: 'order_id',
      key: 'order_id',
      width: 120,
    },
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      width: 120,
      render: (d: string) => dayjs(d).format('MM-DD'),
    },
    {
      title: '股票代码',
      dataIndex: 'code',
      key: 'code',
      width: 100,
    },
    {
      title: '方向',
      dataIndex: 'action',
      key: 'action',
      width: 80,
      render: (action: string) => (
        <Tag color={action === 'buy' ? 'green' : 'red'}>
          {action === 'buy' ? '买入' : '卖出'}
        </Tag>
      ),
    },
    {
      title: '数量',
      dataIndex: 'shares',
      key: 'shares',
      width: 100,
      render: (shares: number) => shares?.toLocaleString(),
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      width: 100,
      render: (price: number) => price?.toFixed(2),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: 'default',
          filled: 'success',
          canceled: 'default',
          rejected: 'error',
        };
        const textMap: Record<string, string> = {
          pending: '待成交',
          filled: '已成交',
          canceled: '已取消',
          rejected: '拒单',
        };
        return <Tag color={colorMap[status]}>{textMap[status]}</Tag>;
      },
    },
  ];

  // ===== 成交记录表格列 =====
  const tradeColumns = [
    {
      title: '成交ID',
      dataIndex: 'trade_id',
      key: 'trade_id',
      width: 120,
    },
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      width: 120,
      render: (d: string) => dayjs(d).format('MM-DD'),
    },
    {
      title: '股票代码',
      dataIndex: 'code',
      key: 'code',
      width: 100,
    },
    {
      title: '方向',
      dataIndex: 'action',
      key: 'action',
      width: 80,
      render: (action: string) => (
        <Tag color={action === 'buy' ? 'green' : 'red'}>
          {action === 'buy' ? '买入' : '卖出'}
        </Tag>
      ),
    },
    {
      title: '数量',
      dataIndex: 'shares',
      key: 'shares',
      width: 100,
      render: (shares: number) => shares?.toLocaleString(),
    },
    {
      title: '成交价',
      dataIndex: 'price',
      key: 'price',
      width: 100,
      render: (price: number) => price?.toFixed(2),
    },
    {
      title: '成交金额',
      key: 'amount',
      width: 140,
      render: (_: any, record: TradeOut) => {
        const amount = (record.shares || 0) * (record.price || 0);
        return amount.toLocaleString();
      },
    },
  ];

  return (
    <div className="page-container">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 20,
        }}
      >
        <div>
          <Title level={4} style={{ margin: 0 }}>
            <DollarCircleOutlined /> 实盘监控
          </Title>
          <Text type="secondary">实时查看持仓、订单、成交记录及交易统计</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setOrderModalVisible(true)}
          >
            下单
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loadingSummary}>
            <Statistic
              title="总资产"
              value={summary?.total_value || 0}
              precision={2}
              prefix="¥"
              valueStyle={{ color: '#1890ff', fontSize: 20 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loadingSummary}>
            <Statistic
              title="当日盈亏"
              value={summary?.today_pnl || 0}
              precision={2}
              prefix="¥"
              valueStyle={{ color: (summary?.today_pnl || 0) >= 0 ? '#52c41a' : '#ff4d4f', fontSize: 20 }}
              prefix={(summary?.today_pnl || 0) >= 0 ? <RiseOutlined /> : <FallOutlined />}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              收益率: {(summary?.today_return_pct || 0) >= 0 ? '+' : ''}
              {(summary?.today_return_pct || 0).toFixed(2)}%
            </Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loadingSummary}>
            <Statistic
              title="持仓市值"
              value={summary?.market_value || 0}
              precision={2}
              prefix="¥"
              valueStyle={{ fontSize: 20 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              持仓 {summary?.position_count || 0} 只
            </Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loadingStats}>
            <Statistic
              title="累计收益"
              value={stats?.total_profit || 0}
              precision={2}
              prefix="¥"
              valueStyle={{ color: '#52c41a', fontSize: 20 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              胜率: {((stats?.win_rate || 0) * 100).toFixed(1)}%
            </Text>
          </Card>
        </Col>
      </Row>

      {/* 净值曲线 + 收益分布 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} lg={16}>
          <Card title="净值曲线" loading={loadingSummary}>
            <ReactECharts option={equityChart} style={{ height: 300 }} opts={{ renderer: 'svg' }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="持仓盈亏分布">
            <ReactECharts option={returnChart} style={{ height: 300 }} opts={{ renderer: 'svg' }} />
          </Card>
        </Col>
      </Row>

      {/* Tab 内容 */}
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        {/* 持仓列表 */}
        <TabPane tab={`持仓列表 (${positions?.length || 0})`} key="positions">
          <Table
            columns={positionColumns}
            dataSource={positions || []}
            rowKey={(record) => `${record.code}-${record.date}`}
            loading={loadingPositions}
            pagination={{ pageSize: 20, showSizeChanger: true }}
          />
        </TabPane>

        {/* 订单列表 */}
        <TabPane tab={`订单记录 (${orders?.total || 0})`} key="orders">
          <Table
            columns={orderColumns}
            dataSource={orders?.items || []}
            rowKey="id"
            loading={loadingOrders}
            pagination={{ pageSize: 20, showSizeChanger: true }}
          />
        </TabPane>

        {/* 成交记录 */}
        <TabPane tab={`成交记录 (${trades?.total || 0})`} key="trades">
          <Table
            columns={tradeColumns}
            dataSource={trades?.items || []}
            rowKey="id"
            loading={loadingTrades}
            pagination={{ pageSize: 20, showSizeChanger: true }}
          />
        </TabPane>

        {/* 交易统计 */}
        <TabPane tab="交易统计" key="stats">
          <Card loading={loadingStats}>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="总成交次数">{stats?.total_trades || 0}</Descriptions.Item>
              <Descriptions.Item label="盈利次数">
                <span style={{ color: '#52c41a' }}>
                  <CheckCircleOutlined /> {stats?.winning_trades || 0}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="亏损次数">
                <span style={{ color: '#ff4d4f' }}>
                  <CloseCircleOutlined /> {stats?.losing_trades || 0}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="胜率">
                <Tag color="blue">{((stats?.win_rate || 0) * 100).toFixed(1)}%</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="累计收益">
                <Text strong style={{ color: '#52c41a', fontSize: 16 }}>
                  +¥{(stats?.total_profit || 0).toLocaleString()}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="平均每笔收益">
                ¥{(stats?.avg_profit_per_trade || 0).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="最大连续盈利次数">
                <Tag color="success">{stats?.max_consecutive_wins || 0}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="最大连续亏损次数">
                <Tag color="error">{stats?.max_consecutive_losses || 0}</Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </TabPane>
      </Tabs>

      {/* 下单弹窗 */}
      <Modal
        title="委托下单"
        open={orderModalVisible}
        onCancel={() => setOrderModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={orderMutation.isPending}
        width={500}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(values) => orderMutation.mutate(values)}
        >
          <Form.Item
            label="股票代码"
            name="code"
            rules={[{ required: true, message: '请输入股票代码' }]}
          >
            <Input placeholder="例如：000001" />
          </Form.Item>

          <Form.Item
            label="操作方向"
            name="action"
            rules={[{ required: true, message: '请选择操作方向' }]}
          >
            <Select placeholder="选择操作">
              <Option value="buy">买入</Option>
              <Option value="sell">卖出</Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="委托数量"
            name="shares"
            rules={[{ required: true, message: '请输入委托数量' }]}
          >
            <InputNumber
              min={100}
              step={100}
              style={{ width: '100%' }}
              placeholder="100的整数倍"
            />
          </Form.Item>

          <Form.Item label="委托价格（选填）" name="price">
            <InputNumber
              min={0.01}
              step={0.01}
              style={{ width: '100%' }}
              placeholder="市价单可不填"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
