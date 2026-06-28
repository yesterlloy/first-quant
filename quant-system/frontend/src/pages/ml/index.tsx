import { useState } from 'react';
import {
  Card,
  Col,
  Row,
  Statistic,
  Typography,
  Table,
  Tabs,
  Tag,
  Button,
  Space,
  message,
  Modal,
  Form,
  Select,
  InputNumber,
  DatePicker,
  Progress,
  Empty,
  Divider,
} from 'antd';
import {
  ThunderboltOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  BarChartOutlined,
  RocketOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import dayjs from 'dayjs';

import {
  getMLModelList,
  getMLTrainTaskList,
  getMLFactorImportance,
  getMLSignals,
  submitMLTrainTask,
  runMLTrainTask,
} from '../../services';
import type {
  MLModelInfo,
  MLTrainTask,
  MLFactorImportance,
  MLTimingSignal,
} from '../../types/data';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;
const { RangePicker } = DatePicker;

/**
 * ML 模型页面
 */
export default function MLModels() {
  const [activeTab, setActiveTab] = useState<string>('tasks');
  const [selectedModel, setSelectedModel] = useState<string>('lgbm');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // ===== 模型列表 =====
  const { data: modelData, isLoading: loadingModels } = useQuery({
    queryKey: ['mlModels'],
    queryFn: () => getMLModelList(),
    staleTime: 10 * 60 * 1000,
  });

  // ===== 训练任务列表 =====
  const {
    data: taskData,
    isLoading: loadingTasks,
    refetch: refetchTasks,
  } = useQuery({
    queryKey: ['mlTasks'],
    queryFn: () => getMLTrainTaskList({ page: 1, page_size: 20 }),
    staleTime: 30 * 1000,
  });

  // ===== 因子重要性 =====
  const {
    data: importanceData,
    isLoading: loadingImportance,
    refetch: refetchImportance,
  } = useQuery({
    queryKey: ['mlImportance'],
    queryFn: () => getMLFactorImportance({ top_n: 20 }),
    staleTime: 5 * 60 * 1000,
  });

  // ===== 预测信号 =====
  const {
    data: signalData,
    isLoading: loadingSignals,
    refetch: refetchSignals,
  } = useQuery({
    queryKey: ['mlSignals'],
    queryFn: () => getMLSignals({ page: 1, page_size: 50 }),
    staleTime: 60 * 1000,
  });

  // ===== 提交训练任务 Mutation =====
  const submitMutation = useMutation({
    mutationFn: (values: any) =>
      submitMLTrainTask({
        model_name: values.model_name,
        start_date: values.date_range?.[0]?.format('YYYY-MM-DD'),
        end_date: values.date_range?.[1]?.format('YYYY-MM-DD'),
        params: {
          n_estimators: values.n_estimators,
          max_depth: values.max_depth,
          learning_rate: values.learning_rate,
        },
      }),
    onSuccess: (data) => {
      message.success('任务提交成功！');
      setIsModalVisible(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['mlTasks'] });

      // 自动执行训练
      runMutation.mutate(data.id);
    },
    onError: (error: any) => {
      message.error(error.message || '提交失败');
    },
  });

  // ===== 执行训练任务 Mutation =====
  const runMutation = useMutation({
    mutationFn: (taskId: number) => runMLTrainTask(taskId),
    onSuccess: () => {
      message.success('训练完成！');
      queryClient.invalidateQueries({ queryKey: ['mlTasks'] });
      queryClient.invalidateQueries({ queryKey: ['mlImportance'] });
      queryClient.invalidateQueries({ queryKey: ['mlSignals'] });
    },
    onError: (error: any) => {
      message.error(error.message || '训练失败');
    },
  });

  // ===== 状态颜色映射 =====
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'default',
      running: 'processing',
      success: 'success',
      failed: 'error',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      pending: '等待中',
      running: '训练中',
      success: '已完成',
      failed: '失败',
    };
    return texts[status] || status;
  };

  const getStatusIcon = (status: string) => {
    const icons: Record<string, React.ReactNode> = {
      pending: <ClockCircleOutlined />,
      running: <ThunderboltOutlined spin />,
      success: <CheckCircleOutlined />,
      failed: <CloseCircleOutlined />,
    };
    return icons[status] || null;
  };

  // ===== 预测颜色 =====
  const getPredictionColor = (prediction?: string) => {
    const colors: Record<string, string> = {
      buy: 'green',
      sell: 'red',
      hold: 'default',
    };
    return colors[prediction || 'hold'] || 'default';
  };

  const getPredictionText = (prediction?: string) => {
    const texts: Record<string, string> = {
      buy: '买入',
      sell: '卖出',
      hold: '持有',
    };
    return texts[prediction || 'hold'] || prediction;
  };

  // ===== 统计数据 =====
  const stats = {
    totalTasks: taskData?.total || 0,
    successTasks: taskData?.items?.filter((t) => t.status === 'success').length || 0,
    runningTasks: taskData?.items?.filter((t) => t.status === 'running').length || 0,
    avgAuc:
      taskData?.items?.filter((t) => t.val_auc).length
      ? taskData.items
        .filter((t) => t.val_auc)
        .reduce((sum, t) => sum + (t.val_auc || 0), 0) /
        taskData.items.filter((t) => t.val_auc).length
      : 0,
  };

  // ===== 因子重要性图表 =====
  const importanceChart: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'value',
      name: '重要性',
    },
    yAxis: {
      type: 'category',
      data: importanceData?.slice(0, 15).map((item) => item.feature_name).reverse() || [],
    },
    series: [
      {
        name: '重要性',
        type: 'bar',
        data: importanceData?.slice(0, 15).map((item) => item.importance).reverse() || [],
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: '#1890ff' },
              { offset: 1, color: '#52c41a' },
            ],
          },
        },
      },
    ],
  };

  // ===== 训练任务表格列 =====
  const taskColumns = [
    {
      title: '任务ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
      width: 100,
      render: (name: string) => {
        const model = modelData?.find((m) => m.name === name);
        return model?.display_name || name;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag icon={getStatusIcon(status)} color={getStatusColor(status)}>
          {getStatusText(status)}
        </Tag>
      ),
    },
    {
      title: '验证集AUC',
      dataIndex: 'val_auc',
      key: 'val_auc',
      width: 120,
      render: (val?: number) => (val ? val.toFixed(4) : '-'),
    },
    {
      title: 'Top组收益',
      dataIndex: 'top_return',
      key: 'top_return',
      width: 120,
      render: (val?: number) => (val ? `${(val * 100).toFixed(2)}%` : '-'),
    },
    {
      title: '特征数',
      dataIndex: 'feature_count',
      key: 'feature_count',
      width: 100,
      render: (val?: number) => val || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (val?: string) => (val ? dayjs(val).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: MLTrainTask) => (
        <Space>
          {record.status === 'pending' && (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => runMutation.mutate(record.id)}
              loading={runMutation.isPending}
            >
              执行
            </Button>
          )}
          {record.status === 'success' && (
            <Button type="link" size="small" onClick={() => message.info('功能开发中')}>
              下载模型
            </Button>
          )}
          {record.status === 'failed' && (
            <Button type="link" size="small" danger onClick={() => message.info(record.error_message)}>
              查看错误
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // ===== 信号表格列 =====
  const signalColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (val: string) => dayjs(val).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '股票代码',
      dataIndex: 'code',
      key: 'code',
      width: 100,
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
      width: 100,
    },
    {
      title: '信号值',
      dataIndex: 'signal',
      key: 'signal',
      width: 100,
      render: (val?: number) => (val !== undefined ? val.toFixed(4) : '-'),
    },
    {
      title: '概率',
      dataIndex: 'probability',
      key: 'probability',
      width: 120,
      render: (val?: number) =>
        val !== undefined ? <Progress percent={val * 100} size="small" /> : '-',
    },
    {
      title: '预测',
      dataIndex: 'prediction',
      key: 'prediction',
      width: 100,
      render: (val?: string) => (
        <Tag color={getPredictionColor(val)}>{getPredictionText(val)}</Tag>
      ),
    },
  ];

  // ===== 刷新 =====
  const handleRefresh = () => {
    message.loading('刷新中...', 0.5).then(() => {
      refetchTasks();
      refetchImportance();
      refetchSignals();
    });
  };

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
            <RocketOutlined /> ML 模型训练
          </Title>
          <Text type="secondary">机器学习因子选股模型训练与预测信号管理</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => setIsModalVisible(true)}>
            新建训练任务
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总任务数"
              value={stats.totalTasks}
              prefix={<RocketOutlined style={{ color: '#1890ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="已完成"
              value={stats.successTasks}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="训练中"
              value={stats.runningTasks}
              valueStyle={{ color: '#1890ff' }}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="平均AUC"
              value={stats.avgAuc}
              precision={4}
              prefix={<BarChartOutlined style={{ color: '#722ed1' }} />}
            />
          </Card>
        </Col>
      </Row>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        {/* 训练任务 */}
        <TabPane tab="训练任务" key="tasks">
          <Card>
            <Table
              columns={taskColumns}
              dataSource={taskData?.items || []}
              rowKey="id"
              loading={loadingTasks || runMutation.isPending}
              pagination={{
                total: taskData?.total || 0,
                pageSize: taskData?.page_size || 20,
                showSizeChanger: true,
                showQuickJumper: true,
              }}
            />
          </Card>
        </TabPane>

        {/* 因子重要性 */}
        <TabPane tab="因子重要性" key="importance">
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card title="Top 15 特征重要性" loading={loadingImportance}>
                {importanceData && importanceData.length > 0 ? (
                  <ReactECharts
                    option={importanceChart}
                    style={{ height: 500 }}
                    opts={{ renderer: 'svg' }}
                  />
                ) : (
                  <Empty description="暂无因子重要性数据，请先运行训练任务" />
                )}
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* 预测信号 */}
        <TabPane tab="预测信号" key="signals">
          <Card title="最新预测信号" loading={loadingSignals}>
            <Table
              columns={signalColumns}
              dataSource={signalData?.items || []}
              rowKey="id"
              pagination={{
                total: signalData?.total || 0,
                pageSize: signalData?.page_size || 20,
                showSizeChanger: true,
                showQuickJumper: true,
              }}
            />
          </Card>
        </TabPane>

        {/* 模型管理 */}
        <TabPane tab="模型管理" key="models">
          <Row gutter={[16, 16]}>
            {modelData?.map((model) => (
              <Col xs={24} sm={12} md={8} key={model.name}>
                <Card
                  hoverable
                  onClick={() => setSelectedModel(model.name)}
                  style={{
                    borderColor: selectedModel === model.name ? '#1890ff' : undefined,
                    boxShadow: selectedModel === model.name ? '0 2px 8px rgba(24, 144, 255, 0.2)' : undefined,
                  }}
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Text strong style={{ fontSize: 16 }}>
                        {model.display_name}
                      </Text>
                      <Tag color={model.type === 'lgbm' ? 'blue' : model.type === 'xgboost' ? 'orange' : 'green'}>
                        {model.type.toUpperCase()}
                      </Tag>
                    </div>
                    <Text type="secondary">{model.description}</Text>
                    <div>
                      <Text type="secondary" style={{ fontSize: 12 }}>支持参数：</Text>
                      <div style={{ marginTop: 4 }}>
                        {model.supported_params.map((p) => (
                          <Tag key={p} color="default" style={{ marginBottom: 4 }}>
                            {p}
                          </Tag>
                        ))}
                      </div>
                    </div>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        </TabPane>
      </Tabs>

      {/* 新建训练任务弹窗 */}
      <Modal
        title="新建训练任务"
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={submitMutation.isPending}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            model_name: 'lgbm',
            n_estimators: 100,
            max_depth: 6,
            learning_rate: 0.1,
          }}
          onFinish={(values) => submitMutation.mutate(values)}
        >
          <Form.Item
            label="选择模型"
            name="model_name"
            rules={[{ required: true, message: '请选择模型' }]}
          >
            <Select placeholder="请选择模型">
              {modelData?.map((model) => (
                <Option key={model.name} value={model.name}>
                  {model.display_name} - {model.description}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item label="训练时间范围" name="date_range">
            <RangePicker
              style={{ width: '100%' }}
              placeholder={['开始日期', '结束日期']}
              disabledDate={(current) => current && current > dayjs().endOf('day')}
            />
          </Form.Item>

          <Divider orientation="left">超参数</Divider>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="树的数量"
                name="n_estimators"
                rules={[{ required: true, message: '请输入树的数量' }]}
              >
                <InputNumber min={10} max={1000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="最大深度"
                name="max_depth"
                rules={[{ required: true, message: '请输入最大深度' }]}
              >
                <InputNumber min={1} max={20} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="学习率"
                name="learning_rate"
                rules={[{ required: true, message: '请输入学习率' }]}
              >
                <InputNumber min={0.001} max={1} step={0.001} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
}