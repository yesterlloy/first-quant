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
  Select,
  InputNumber,
  Switch,
  message,
  Tabs,
  Descriptions,
  Progress,
} from 'antd';
import {
  ClockCircleOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
  CalendarOutlined,
  BarChartOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import dayjs from 'dayjs';

import {
  getSchedulerStats,
  getSchedulerTasks,
  getSchedulerLogs,
  createSchedulerTask,
  updateSchedulerTask,
  toggleSchedulerTask,
  deleteSchedulerTask,
  triggerSchedulerTask,
  initDefaultTasks,
} from '../../services';
import type { SchedulerTaskOut, SchedulerLogOut } from '../../types/data';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;
const { TextArea } = Input;

/**
 * 任务调度中心页面
 */
export default function SchedulerCenter() {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [taskModalVisible, setTaskModalVisible] = useState(false);
  const [editingTask, setEditingTask] = useState<SchedulerTaskOut | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // ===== 调度器统计 =====
  const { data: stats, isLoading: loadingStats, refetch: refetchStats } = useQuery({
    queryKey: ['schedulerStats'],
    queryFn: () => getSchedulerStats(),
    staleTime: 30 * 1000,
  });

  // ===== 任务列表 =====
  const { data: tasksData, isLoading: loadingTasks, refetch: refetchTasks } = useQuery({
    queryKey: ['schedulerTasks'],
    queryFn: () => getSchedulerTasks({ page_size: 50 }),
    staleTime: 60 * 1000,
  });

  // ===== 执行日志 =====
  const { data: logsData, isLoading: loadingLogs, refetch: refetchLogs } = useQuery({
    queryKey: ['schedulerLogs'],
    queryFn: () => getSchedulerLogs({ page_size: 50 }),
    staleTime: 30 * 1000,
  });

  // ===== 任务表格列 =====
  const taskColumns = [
    {
      title: '任务名称',
      dataIndex: 'task_name',
      key: 'task_name',
      width: 180,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: 'Cron 表达式',
      dataIndex: 'cron',
      key: 'cron',
      width: 150,
      render: (cron: string) => (
        <Tag icon={<CalendarOutlined />} color="blue">
          {cron}
        </Tag>
      ),
    },
    {
      title: '超时(秒)',
      dataIndex: 'timeout',
      key: 'timeout',
      width: 100,
    },
    {
      title: '重试',
      dataIndex: 'retry',
      key: 'retry',
      width: 80,
      render: (retry: boolean, record: SchedulerTaskOut) => (
        <Tag color={retry ? 'green' : 'default'}>
          {retry ? `最多${record.retry_max}次` : '不重试'}
        </Tag>
      ),
    },
    {
      title: '上次执行',
      dataIndex: 'last_run_at',
      key: 'last_run_at',
      width: 150,
      render: (ts: string, record: SchedulerTaskOut) => {
        const colors: Record<string, string> = {
          success: 'green',
          running: 'blue',
          failed: 'red',
          skipped: 'orange',
        };
        return (
          <Space size="small">
            {ts && dayjs(ts).format('MM-DD HH:mm')}
            {record.last_status && (
              <Tag color={colors[record.last_status] || 'default'}>
                {record.last_status}
              </Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 100,
      render: (enabled: boolean, record: SchedulerTaskOut) => (
        <Switch
          checked={enabled}
          checkedChildren="启用"
          unCheckedChildren="禁用"
          onChange={(checked) => handleToggleTask(record.id, checked)}
        />
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      fixed: 'right' as const,
      render: (_: any, record: SchedulerTaskOut) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => handleTriggerTask(record.task_name)}
          >
            触发
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditTask(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteTask(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  // ===== 日志表格列 =====
  const logColumns = [
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 160,
      render: (ts: string) => dayjs(ts).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '任务名称',
      dataIndex: 'task_name',
      key: 'task_name',
      width: 150,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const colors: Record<string, string> = {
          success: 'green',
          running: 'blue',
          failed: 'red',
          skipped: 'orange',
        };
        const icons: Record<string, React.ReactNode> = {
          success: <CheckCircleOutlined />,
          running: <ClockCircleOutlined />,
          failed: <CloseCircleOutlined />,
          skipped: <CloseCircleOutlined />,
        };
        return (
          <Tag icon={icons[status]} color={colors[status] || 'default'}>
            {status}
          </Tag>
        );
      },
    },
    {
      title: '耗时(秒)',
      dataIndex: 'duration_seconds',
      key: 'duration_seconds',
      width: 100,
      render: (sec: number) => sec?.toFixed(2) || '-',
    },
    {
      title: '重试次数',
      dataIndex: 'retry_count',
      key: 'retry_count',
      width: 100,
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
      render: (msg: string) => msg || '-',
    },
  ];

  // ===== 启用/禁用任务 Mutation =====
  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      toggleSchedulerTask(id, enabled),
    onSuccess: () => {
      message.success('任务状态已更新');
      queryClient.invalidateQueries({ queryKey: ['schedulerTasks'] });
    },
    onError: (error: any) => {
      message.error(error.message || '更新失败');
    },
  });

  // ===== 保存任务 Mutation =====
  const saveTaskMutation = useMutation({
    mutationFn: (values: any) => {
      if (editingTask) {
        return updateSchedulerTask(editingTask.id, values);
      }
      return createSchedulerTask(values);
    },
    onSuccess: () => {
      message.success(editingTask ? '任务已更新' : '任务已创建');
      setTaskModalVisible(false);
      form.resetFields();
      setEditingTask(null);
      queryClient.invalidateQueries({ queryKey: ['schedulerTasks'] });
    },
    onError: (error: any) => {
      message.error(error.message || '保存失败');
    },
  });

  // ===== 删除任务 Mutation =====
  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteSchedulerTask(id),
    onSuccess: () => {
      message.success('任务已删除');
      queryClient.invalidateQueries({ queryKey: ['schedulerTasks'] });
    },
    onError: (error: any) => {
      message.error(error.message || '删除失败');
    },
  });

  // ===== 触发任务 Mutation =====
  const triggerMutation = useMutation({
    mutationFn: (taskName: string) => triggerSchedulerTask(taskName),
    onSuccess: (result) => {
      message.success(result.message || `任务 ${result.task_name} 已触发`);
      queryClient.invalidateQueries({ queryKey: ['schedulerLogs'] });
      queryClient.invalidateQueries({ queryKey: ['schedulerStats'] });
    },
    onError: (error: any) => {
      message.error(error.message || '触发失败');
    },
  });

  // ===== 初始化默认任务 Mutation =====
  const initMutation = useMutation({
    mutationFn: () => initDefaultTasks(),
    onSuccess: () => {
      message.success('默认任务已初始化');
      queryClient.invalidateQueries({ queryKey: ['schedulerTasks'] });
    },
    onError: (error: any) => {
      message.error(error.message || '初始化失败');
    },
  });

  const handleToggleTask = (id: number, enabled: boolean) => {
    toggleMutation.mutate({ id, enabled });
  };

  const handleEditTask = (task: SchedulerTaskOut) => {
    setEditingTask(task);
    form.setFieldsValue({
      task_name: task.task_name,
      cron: task.cron,
      enabled: task.enabled,
      timeout: task.timeout,
      retry: task.retry,
      retry_max: task.retry_max,
      description: task.description,
    });
    setTaskModalVisible(true);
  };

  const handleDeleteTask = (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除此调度任务吗？',
      okText: '确定',
      cancelText: '取消',
      okType: 'danger',
      onOk: () => deleteMutation.mutate(id),
    });
  };

  const handleTriggerTask = (taskName: string) => {
    Modal.confirm({
      title: '确认触发',
      content: `确定要手动触发任务 "${taskName}" 吗？`,
      okText: '触发',
      cancelText: '取消',
      onOk: () => triggerMutation.mutate(taskName),
    });
  };

  const handleAddTask = () => {
    setEditingTask(null);
    form.resetFields();
    form.setFieldsValue({
      enabled: true,
      timeout: 300,
      retry: true,
      retry_max: 3,
    });
    setTaskModalVisible(true);
  };

  const handleSaveTask = (values: any) => {
    saveTaskMutation.mutate(values);
  };

  const handleRefresh = () => {
    message.loading('刷新中...', 0.5).then(() => {
      refetchStats();
      refetchTasks();
      refetchLogs();
    });
  };

  // ===== 执行状态图表 =====
  const statusChart: EChartsOption = {
    tooltip: {
      trigger: 'item',
    },
    legend: {
      bottom: 0,
      left: 'center',
    },
    series: [
      {
        name: '执行统计',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: false,
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold',
          },
        },
        data: [
          { value: stats?.success_count || 0, name: '成功', itemStyle: { color: '#52c41a' } },
          { value: stats?.failed_count || 0, name: '失败', itemStyle: { color: '#ff4d4f' } },
          { value: (stats?.today_runs || 0) - (stats?.success_count || 0) - (stats?.failed_count || 0), name: '其他', itemStyle: { color: '#d9d9d9' } },
        ],
      },
    ],
  };

  // ===== 任务执行耗时图表 =====
  const durationChart: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ['平均耗时'],
    },
    yAxis: {
      type: 'value',
      name: '秒',
    },
    series: [
      {
        name: '平均耗时',
        type: 'bar',
        data: [stats?.avg_duration || 0],
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#1890ff' },
              { offset: 1, color: '#722ed1' },
            ],
          },
        },
      },
    ],
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
            <SettingOutlined /> 任务调度中心
          </Title>
          <Text type="secondary">定时任务管理、执行监控、日志查看</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
          <Button icon={<PlayCircleOutlined />} onClick={() => initMutation.mutate()}>
            初始化默认任务
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAddTask}>
            新增任务
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} sm={12} md={4}>
          <Card loading={loadingStats}>
            <Statistic
              title="任务总数"
              value={stats?.total_tasks || 0}
              prefix={<CalendarOutlined style={{ color: '#1890ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card loading={loadingStats}>
            <Statistic
              title="已启用任务"
              value={stats?.enabled_tasks || 0}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card loading={loadingStats}>
            <Statistic
              title="今日执行"
              value={stats?.today_runs || 0}
              prefix={<PlayCircleOutlined style={{ color: '#722ed1' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card loading={loadingStats}>
            <Statistic
              title="成功次数"
              value={stats?.success_count || 0}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card loading={loadingStats}>
            <Statistic
              title="失败次数"
              value={stats?.failed_count || 0}
              prefix={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card loading={loadingStats}>
            <Statistic
              title="平均耗时(秒)"
              value={stats?.avg_duration || 0}
              precision={2}
              prefix={<ClockCircleOutlined style={{ color: '#fa8c16' }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* 运行中任务提示 */}
      {stats?.running_tasks && stats.running_tasks.length > 0 && (
        <Card
          style={{ marginBottom: 20 }}
          bodyStyle={{ padding: '12px 24px' }}
        >
          <Space>
            <Progress type="circle" percent={100} loading size="small" />
            <Text strong>正在运行: </Text>
            {stats.running_tasks.map(task => (
              <Tag key={task} color="blue">{task}</Tag>
            ))}
          </Space>
        </Card>
      )}

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        {/* 概览 */}
        <TabPane tab="概览" key="overview">
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card title="今日执行状态分布" loading={loadingStats}>
                <ReactECharts option={statusChart} style={{ height: 300 }} opts={{ renderer: 'svg' }} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="任务执行耗时" loading={loadingStats}>
                <ReactECharts option={durationChart} style={{ height: 300 }} opts={{ renderer: 'svg' }} />
              </Card>
            </Col>
          </Row>

          {/* 最近失败任务 */}
          {stats?.recently_failed && stats.recently_failed.length > 0 && (
            <Card title="最近失败任务" style={{ marginTop: 16 }}>
              {stats.recently_failed.map((item, index) => (
                <Descriptions key={index} bordered size="small" style={{ marginBottom: 8 }}>
                  <Descriptions.Item label="任务名称" span={3}>
                    <Text strong type="danger">{item.task_name}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="失败时间" span={3}>
                    {item.failed_at ? dayjs(item.failed_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="错误信息" span={3}>
                    <Text type="danger">{item.error_message || '未知错误'}</Text>
                  </Descriptions.Item>
                </Descriptions>
              ))}
            </Card>
          )}
        </TabPane>

        {/* 任务管理 */}
        <TabPane tab="任务管理" key="tasks">
          <Table
            columns={taskColumns}
            dataSource={tasksData?.items || []}
            rowKey="id"
            loading={loadingTasks || toggleMutation.isPending}
            pagination={{
              total: tasksData?.total || 0,
              pageSize: tasksData?.page_size || 20,
              showSizeChanger: true,
            }}
            scroll={{ x: 1300 }}
          />
        </TabPane>

        {/* 执行日志 */}
        <TabPane tab="执行日志" key="logs">
          <Table
            columns={logColumns}
            dataSource={logsData?.items || []}
            rowKey="id"
            loading={loadingLogs}
            pagination={{
              total: logsData?.total || 0,
              pageSize: logsData?.page_size || 20,
              showSizeChanger: true,
            }}
            scroll={{ x: 1200 }}
          />
        </TabPane>
      </Tabs>

      {/* 任务编辑弹窗 */}
      <Modal
        title={editingTask ? '编辑调度任务' : '新增调度任务'}
        open={taskModalVisible}
        onCancel={() => setTaskModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={saveTaskMutation.isPending}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSaveTask}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="任务名称"
                name="task_name"
                rules={[{ required: true, message: '请输入任务名称' }]}
              >
                <Input placeholder="例如：每日数据采集" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Cron 表达式"
                name="cron"
                rules={[{ required: true, message: '请输入 Cron 表达式' }]}
              >
                <Select placeholder="选择或输入 Cron">
                  <Option value="0 18 * * 1-5">工作日 18:00</Option>
                  <Option value="0 19 * * 1-5">工作日 19:00</Option>
                  <Option value="0 20 * * 1-5">工作日 20:00</Option>
                  <Option value="0 14 L * *">每月最后一天 14:00</Option>
                  <Option value="0 18 * * 5">每周五 18:00</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="超时时间(秒)"
                name="timeout"
                rules={[{ required: true, message: '请输入超时时间' }]}
              >
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="是否重试"
                name="retry"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="最大重试次数"
                name="retry_max"
              >
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="状态"
            name="enabled"
            valuePropName="checked"
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item
            label="任务描述"
            name="description"
          >
            <TextArea rows={3} placeholder="简要描述此任务的作用" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}