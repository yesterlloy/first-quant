import { useState } from 'react';
import {
  Card,
  Col,
  Row,
  Statistic,
  Typography,
  Table,
  Select,
  InputNumber,
  Button,
  Form,
  Spin,
  Progress,
  Descriptions,
  Alert,
  Space,
  message,
} from 'antd';
import {
  PlayCircleOutlined,
  BarChartOutlined,
  RiseOutlined,
  FallOutlined,
  ThunderboltOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import dayjs from 'dayjs';

import { getStrategyList, submitBacktest, getBacktestTask, getBacktestResult } from '../../services';
import type { StrategyInfo, BacktestTask, BacktestResult } from '../../types/data';

const { Title } = Typography;

/**
 * 策略回测页面
 */
export default function StrategyBacktest() {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null);
  const [pollingCount, setPollingCount] = useState(0);

  // ===== 策略列表 =====
  const { data: strategies, isLoading: loadingStrategies } = useQuery({
    queryKey: ['strategyList'],
    queryFn: () => getStrategyList(),
    staleTime: 10 * 60 * 1000,
  });

  // ===== 提交回测任务 =====
  const submitMutation = useMutation({
    mutationFn: submitBacktest,
    onSuccess: (data) => {
      message.success('回测任务已提交');
      setRunningTaskId(data.task_id);
      setPollingCount(0);
    },
    onError: (error) => {
      message.error(`提交失败: ${error}`);
    },
  });

  // ===== 查询任务状态（轮询）=====
  const { data: taskStatus, isLoading: loadingTaskStatus } = useQuery({
    queryKey: ['backtestTask', runningTaskId, pollingCount],
    queryFn: () => getBacktestTask(runningTaskId!),
    enabled: !!runningTaskId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // 任务完成后停止轮询
      if (data && ['completed', 'failed'].includes(data.status)) {
        return false;
      }
      return 2000; // 每 2 秒更新
    },
  });

  // ===== 获取回测结果 =====
  const { data: backtestResult, isLoading: loadingResult } = useQuery({
    queryKey: ['backtestResult', runningTaskId],
    queryFn: () => getBacktestResult(runningTaskId!),
    enabled: !!runningTaskId && taskStatus?.status === 'completed',
  });

  // 提交回测
  const handleSubmit = (values: Record<string, string | number>) => {
    submitMutation.mutate({
      strategy_id: values.strategy_id as string,
      stock_code: values.stock_code as string,
      start_date: dayjs(values.start_date).format('YYYY-MM-DD'),
      end_date: dayjs(values.end_date).format('YYYY-MM-DD'),
      initial_capital: values.initial_capital as number,
      params: {
        short_window: values.short_window as number,
        long_window: values.long_window as number,
      },
    });
  };

  // 净值曲线配置
  const equityChartOption: EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['策略净值', '基准净值'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: (backtestResult?.equity_curve || []).map((p) => p.date),
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '策略净值',
        type: 'line',
        smooth: true,
        data: (backtestResult?.equity_curve || []).map((p) => p.value.toFixed(2)),
        lineStyle: { color: '#cf1322', width: 2 },
        areaStyle: { color: 'rgba(207, 19, 34, 0.1)' },
      },
    ],
  };

  // 回撤曲线配置
  const drawdownChartOption: EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['回撤率'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: (backtestResult?.drawdown_curve || []).map((p) => p.date),
    },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      {
        name: '回撤率',
        type: 'line',
        smooth: true,
        data: (backtestResult?.drawdown_curve || []).map((p) => (p.value * 100).toFixed(2)),
        lineStyle: { color: '#3f8600', width: 2 },
        areaStyle: { color: 'rgba(63, 134, 0, 0.1)' },
      },
    ],
  };

  const showResult = taskStatus?.status === 'completed' && backtestResult;
  const isRunning = taskStatus?.status === 'running';

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      <Title level={3} style={{ marginBottom: 20 }}>
        🎮 策略回测
      </Title>

      <Row gutter={[16, 16]}>
        {/* 左侧：参数配置 */}
        <Col xs={24} lg={8}>
          <Card title="⚙️ 回测参数">
            <Form
              form={form}
              layout="vertical"
              initialValues={{
                strategy_id: 'ma_cross',
                stock_code: '000001',
                start_date: dayjs().subtract(1, 'year').toDate(),
                end_date: dayjs().toDate(),
                initial_capital: 1000000,
                short_window: 5,
                long_window: 20,
              }}
              onFinish={handleSubmit}
            >
              <Form.Item name="strategy_id" label="选择策略" rules={[{ required: true }]}>
                <Select loading={loadingStrategies}>
                  {(strategies || []).map((s: StrategyInfo) => (
                    <Select.Option key={s.id} value={s.id}>
                      {s.name} - {s.description}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item name="stock_code" label="股票代码" rules={[{ required: true }]}>
                <Select>
                  <Select.Option value="000001">000001 平安银行</Select.Option>
                  <Select.Option value="000002">000002 万科A</Select.Option>
                  <Select.Option value="600519">600519 贵州茅台</Select.Option>
                </Select>
              </Form.Item>

              <Form.Item name="start_date" label="开始日期" rules={[{ required: true }]}>
                <InputNumber
                  style={{ width: '100%' }}
                  formatter={(value) => dayjs(value).format('YYYY-MM-DD')}
                />
              </Form.Item>

              <Form.Item name="end_date" label="结束日期" rules={[{ required: true }]}>
                <InputNumber
                  style={{ width: '100%' }}
                  formatter={(value) => dayjs(value).format('YYYY-MM-DD')}
                />
              </Form.Item>

              <Form.Item name="initial_capital" label="初始资金" rules={[{ required: true }]}>
                <InputNumber
                  style={{ width: '100%' }}
                  min={10000}
                  formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                />
              </Form.Item>

              <Form.Item label="策略参数">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Form.Item name="short_window" label="短周期" noStyle rules={[{ required: true }]}>
                    <InputNumber style={{ width: '100%' }} min={1} max={60} />
                  </Form.Item>
                  <Form.Item name="long_window" label="长周期" noStyle rules={[{ required: true }]}>
                    <InputNumber style={{ width: '100%' }} min={5} max={250} />
                  </Form.Item>
                </Space>
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  block
                  size="large"
                  icon={<PlayCircleOutlined />}
                  loading={submitMutation.isPending || isRunning}
                >
                  {isRunning ? '回测中...' : '开始回测'}
                </Button>
              </Form.Item>
            </Form>
          </Card>

          {/* 任务进度 */}
          {isRunning && (
            <Card title="🔄 回测进度" style={{ marginTop: 16 }}>
              <Progress percent={Math.round((taskStatus?.progress || 0) * 100)} status="active" />
              <div style={{ marginTop: 8, textAlign: 'center', color: '#999' }}>
                {taskStatus?.progress !== undefined && `${Math.round(taskStatus.progress * 100)}% 完成`}
              </div>
            </Card>
          )}

          {/* 错误提示 */}
          {taskStatus?.status === 'failed' && (
            <Alert
              message="回测失败"
              description={taskStatus.error_message || '未知错误'}
              type="error"
              showIcon
              style={{ marginTop: 16 }}
            />
          )}
        </Col>

        {/* 右侧：回测结果 */}
        <Col xs={24} lg={16}>
          {/* 指标卡片 */}
          {showResult && (
            <>
              <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                <Col xs={24} sm={12} lg={6}>
                  <Card>
                    <Statistic
                      title="总收益率"
                      value={backtestResult.metrics.total_return * 100}
                      precision={2}
                      suffix="%"
                      valueStyle={{ color: backtestResult.metrics.total_return >= 0 ? '#cf1322' : '#3f8600' }}
                      prefix={<TrophyOutlined />}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card>
                    <Statistic
                      title="年化收益率"
                      value={backtestResult.metrics.annual_return * 100}
                      precision={2}
                      suffix="%"
                      valueStyle={{ color: backtestResult.metrics.annual_return >= 0 ? '#cf1322' : '#3f8600' }}
                      prefix={<RiseOutlined />}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card>
                    <Statistic
                      title="夏普比率"
                      value={backtestResult.metrics.sharpe_ratio}
                      precision={2}
                      valueStyle={{ color: backtestResult.metrics.sharpe_ratio >= 1 ? '#52c41a' : '#fa8c16' }}
                      prefix={<ThunderboltOutlined />}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card>
                    <Statistic
                      title="最大回撤"
                      value={Math.abs(backtestResult.metrics.max_drawdown) * 100}
                      precision={2}
                      suffix="%"
                      valueStyle={{ color: '#3f8600' }}
                      prefix={<FallOutlined />}
                    />
                  </Card>
                </Col>
              </Row>

              {/* 净值曲线 */}
              <Card title="📈 净值曲线" style={{ marginBottom: 16 }}>
                <Spin spinning={loadingResult}>
                  <ReactECharts option={equityChartOption} style={{ height: 300 }} />
                </Spin>
              </Card>

              {/* 回撤曲线 */}
              <Card title="📉 回撤曲线" style={{ marginBottom: 16 }}>
                <Spin spinning={loadingResult}>
                  <ReactECharts option={drawdownChartOption} style={{ height: 280 }} />
                </Spin>
              </Card>

              {/* 详细指标 */}
              <Card title="📊 详细指标">
                <Descriptions bordered column={2}>
                  <Descriptions.Item label="策略名称">{backtestResult.strategy_name}</Descriptions.Item>
                  <Descriptions.Item label="回测股票">{backtestResult.stock_code}</Descriptions.Item>
                  <Descriptions.Item label="回测区间">
                    {backtestResult.start_date} ~ {backtestResult.end_date}
                  </Descriptions.Item>
                  <Descriptions.Item label="初始资金">
                    {backtestResult.initial_capital.toLocaleString()}
                  </Descriptions.Item>
                  <Descriptions.Item label="最终资金">
                    {backtestResult.final_capital.toLocaleString()}
                  </Descriptions.Item>
                  <Descriptions.Item label="总收益率">
                    {(backtestResult.metrics.total_return * 100).toFixed(2)}%
                  </Descriptions.Item>
                  <Descriptions.Item label="夏普比率">
                    {backtestResult.metrics.sharpe_ratio.toFixed(2)}
                  </Descriptions.Item>
                  <Descriptions.Item label="最大回撤">
                    {(Math.abs(backtestResult.metrics.max_drawdown) * 100).toFixed(2)}%
                  </Descriptions.Item>
                  <Descriptions.Item label="胜率">
                    {(backtestResult.metrics.win_rate * 100).toFixed(2)}%
                  </Descriptions.Item>
                  <Descriptions.Item label="盈亏比">
                    {backtestResult.metrics.profit_loss_ratio.toFixed(2)}
                  </Descriptions.Item>
                  <Descriptions.Item label="交易次数">
                    {backtestResult.metrics.total_trades}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </>
          )}

          {/* 空状态 */}
          {!showResult && !isRunning && (
            <Card>
              <div style={{ textAlign: 'center', padding: '80px 0', color: '#999' }}>
                <BarChartOutlined style={{ fontSize: 64, marginBottom: 16 }} />
                <p>选择策略并配置参数，点击开始回测查看结果</p>
              </div>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}
