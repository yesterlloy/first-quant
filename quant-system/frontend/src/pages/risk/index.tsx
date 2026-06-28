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
} from 'antd';
import {
  WarningOutlined,
  StopOutlined,
  SafetyOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import dayjs from 'dayjs';

import {
  getRiskStats,
  getRiskRules,
  getRiskEvents,
  createRiskRule,
  updateRiskRule,
  toggleRiskRule,
  deleteRiskRule,
  checkRisk,
} from '../../services';
import type { RiskRuleOut, RiskEventOut, RiskCheckResult, RiskStatsOut } from '../../types/data';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;
const { TextArea } = Input;

/**
 * 风控中心页面
 */
export default function RiskCenter() {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [ruleModalVisible, setRuleModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<RiskRuleOut | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // ===== 风控统计 =====
  const { data: stats, isLoading: loadingStats, refetch: refetchStats } = useQuery({
    queryKey: ['riskStats'],
    queryFn: () => getRiskStats(),
    staleTime: 30 * 1000,
  });

  // ===== 风控规则列表 =====
  const { data: rulesData, isLoading: loadingRules, refetch: refetchRules } = useQuery({
    queryKey: ['riskRules'],
    queryFn: () => getRiskRules({ page_size: 50 }),
    staleTime: 60 * 1000,
  });

  // ===== 风控事件列表 =====
  const { data: eventsData, isLoading: loadingEvents, refetch: refetchEvents } = useQuery({
    queryKey: ['riskEvents'],
    queryFn: () => getRiskEvents({ page_size: 50 }),
    staleTime: 30 * 1000,
  });

  // ===== 风控规则表格列 =====
  const ruleColumns = [
    {
      title: '规则名称',
      dataIndex: 'rule_name',
      key: 'rule_name',
      width: 200,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: '类型',
      dataIndex: 'rule_type',
      key: 'rule_type',
      width: 180,
    },
    {
      title: '等级',
      dataIndex: 'level',
      key: 'level',
      width: 100,
      render: (level: string) => {
        const colors: Record<string, string> = {
          info: 'blue',
          warning: 'orange',
          block: 'red',
        };
        const labels: Record<string, string> = {
          info: '提示',
          warning: '警告',
          block: '阻断',
        };
        return <Tag color={colors[level]}>{labels[level] || level}</Tag>;
      },
    },
    {
      title: '参数',
      dataIndex: 'params',
      key: 'params',
      width: 200,
      render: (params: any) => (
        <Text type="secondary" ellipsis style={{ maxWidth: 180 }}>
          {JSON.stringify(params)}
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 100,
      render: (enabled: boolean, record: RiskRuleOut) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleToggleRule(record.id, checked)}
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
      width: 150,
      fixed: 'right' as const,
      render: (_: any, record: RiskRuleOut) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditRule(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteRule(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  // ===== 风控事件表格列 =====
  const eventColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (ts: string) => dayjs(ts).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '等级',
      dataIndex: 'level',
      key: 'level',
      width: 100,
      render: (level: string) => {
        const icons: Record<string, React.ReactNode> = {
          info: <SafetyOutlined style={{ color: '#1890ff' }} />,
          warning: <WarningOutlined style={{ color: '#faad14' }} />,
          block: <StopOutlined style={{ color: '#ff4d4f' }} />,
        };
        const colors: Record<string, string> = {
          info: 'blue',
          warning: 'orange',
          block: 'red',
        };
        const labels: Record<string, string> = {
          info: '提示',
          warning: '警告',
          block: '阻断',
        };
        return (
          <Tag icon={icons[level]} color={colors[level]}>
            {labels[level] || level}
          </Tag>
        );
      },
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 150,
    },
    {
      title: '股票代码',
      dataIndex: 'code',
      key: 'code',
      width: 120,
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
  ];

  // ===== 启用/禁用规则 Mutation =====
  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      toggleRiskRule(id, enabled),
    onSuccess: () => {
      message.success('规则状态已更新');
      queryClient.invalidateQueries({ queryKey: ['riskRules'] });
    },
    onError: (error: any) => {
      message.error(error.message || '更新失败');
    },
  });

  // ===== 保存规则 Mutation =====
  const saveRuleMutation = useMutation({
    mutationFn: (values: any) => {
      if (editingRule) {
        return updateRiskRule(editingRule.id, values);
      }
      return createRiskRule(values);
    },
    onSuccess: () => {
      message.success(editingRule ? '规则已更新' : '规则已创建');
      setRuleModalVisible(false);
      form.resetFields();
      setEditingRule(null);
      queryClient.invalidateQueries({ queryKey: ['riskRules'] });
    },
    onError: (error: any) => {
      message.error(error.message || '保存失败');
    },
  });

  // ===== 删除规则 Mutation =====
  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteRiskRule(id),
    onSuccess: () => {
      message.success('规则已删除');
      queryClient.invalidateQueries({ queryKey: ['riskRules'] });
    },
    onError: (error: any) => {
      message.error(error.message || '删除失败');
    },
  });

  // ===== 风控检查 Mutation =====
  const checkRiskMutation = useMutation({
    mutationFn: (values: any) => checkRisk(values),
    onSuccess: (result) => {
      const status = result.passed ? '✅ 通过' : '❌ 阻止';
      message.info(`风控检查结果: ${status}`);
      queryClient.invalidateQueries({ queryKey: ['riskEvents'] });
      queryClient.invalidateQueries({ queryKey: ['riskStats'] });
    },
    onError: (error: any) => {
      message.error(error.message || '检查失败');
    },
  });

  const handleToggleRule = (id: number, enabled: boolean) => {
    toggleMutation.mutate({ id, enabled });
  };

  const handleEditRule = (rule: RiskRuleOut) => {
    setEditingRule(rule);
    form.setFieldsValue({
      rule_name: rule.rule_name,
      rule_type: rule.rule_type,
      level: rule.level,
      enabled: rule.enabled,
      description: rule.description,
      params: rule.params ? JSON.stringify(rule.params, null, 2) : '{}',
    });
    setRuleModalVisible(true);
  };

  const handleDeleteRule = (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除此风控规则吗？',
      okText: '确定',
      cancelText: '取消',
      okType: 'danger',
      onOk: () => deleteMutation.mutate(id),
    });
  };

  const handleAddRule = () => {
    setEditingRule(null);
    form.resetFields();
    form.setFieldsValue({
      level: 'warning',
      enabled: true,
      params: '{}',
    });
    setRuleModalVisible(true);
  };

  const handleSaveRule = (values: any) => {
    try {
      const params = values.params ? JSON.parse(values.params) : {};
      saveRuleMutation.mutate({ ...values, params });
    } catch (e) {
      message.error('参数 JSON 格式错误');
    }
  };

  const handleRefresh = () => {
    message.loading('刷新中...', 0.5).then(() => {
      refetchStats();
      refetchRules();
      refetchEvents();
    });
  };

  // ===== 风控等级分布图表 =====
  const levelChart: EChartsOption = {
    tooltip: {
      trigger: 'item',
    },
    legend: {
      bottom: 0,
      left: 'center',
    },
    series: [
      {
        name: '事件分布',
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
          { value: stats?.today_events || 0, name: '今日事件', itemStyle: { color: '#1890ff' } },
          { value: (stats?.warning_count || 0) - (stats?.today_events || 0), name: '历史警告', itemStyle: { color: '#faad14' } },
          { value: stats?.block_count || 0, name: '阻断事件', itemStyle: { color: '#ff4d4f' } },
        ],
      },
    ],
  };

  // ===== 触发频率图表 =====
  const triggerChart: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: stats?.top_triggers?.map((t) => t.type) || [],
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        name: '触发次数',
        type: 'bar',
        data: stats?.top_triggers?.map((t) => t.count) || [],
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#1890ff' },
              { offset: 1, color: '#52c41a' },
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
            <SafetyOutlined /> 风控中心
          </Title>
          <Text type="secondary">风险管理、规则配置、事件监控</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAddRule}>
            新增规则
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loadingStats}>
            <Statistic
              title="风控规则总数"
              value={stats?.total_rules || 0}
              prefix={<SafetyOutlined style={{ color: '#1890ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loadingStats}>
            <Statistic
              title="已启用规则"
              value={stats?.enabled_rules || 0}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loadingStats}>
            <Statistic
              title="今日事件"
              value={stats?.today_events || 0}
              prefix={<WarningOutlined style={{ color: '#faad14' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loadingStats}>
            <Statistic
              title="阻断次数"
              value={stats?.block_count || 0}
              prefix={<StopOutlined style={{ color: '#ff4d4f' }} />}
            />
          </Card>
        </Col>
      </Row>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        {/* 概览 */}
        <TabPane tab="概览" key="overview">
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card title="事件分布" loading={loadingStats}>
                <ReactECharts option={levelChart} style={{ height: 300 }} opts={{ renderer: 'svg' }} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="规则触发 Top 5" loading={loadingStats}>
                <ReactECharts option={triggerChart} style={{ height: 300 }} opts={{ renderer: 'svg' }} />
              </Card>
            </Col>
          </Row>

          {/* 快速风控检查 */}
          <Card title="快速风控检查" style={{ marginTop: 16 }}>
            <Form
              layout="inline"
              initialValues={{ action: 'buy' }}
              onFinish={(values) => checkRiskMutation.mutate(values)}
            >
              <Form.Item name="action" label="操作类型" rules={[{ required: true }]}>
                <Select style={{ width: 120 }}>
                  <Option value="buy">买入</Option>
                  <Option value="sell">卖出</Option>
                </Select>
              </Form.Item>
              <Form.Item name="code" label="股票代码">
                <Input placeholder="例如：000001" style={{ width: 150 }} />
              </Form.Item>
              <Form.Item name="shares" label="数量">
                <InputNumber min={1} placeholder="数量" style={{ width: 120 }} />
              </Form.Item>
              <Form.Item name="price" label="价格">
                <InputNumber min={0.01} step={0.01} placeholder="价格" style={{ width: 120 }} />
              </Form.Item>
              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={checkRiskMutation.isPending}
                  icon={<SafetyOutlined />}
                >
                  执行检查
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>

        {/* 规则管理 */}
        <TabPane tab="规则管理" key="rules">
          <Table
            columns={ruleColumns}
            dataSource={rulesData?.items || []}
            rowKey="id"
            loading={loadingRules || toggleMutation.isPending}
            pagination={{
              total: rulesData?.total || 0,
              pageSize: rulesData?.page_size || 20,
              showSizeChanger: true,
            }}
            scroll={{ x: 1200 }}
          />
        </TabPane>

        {/* 事件日志 */}
        <TabPane tab="事件日志" key="events">
          <Table
            columns={eventColumns}
            dataSource={eventsData?.items || []}
            rowKey="id"
            loading={loadingEvents}
            pagination={{
              total: eventsData?.total || 0,
              pageSize: eventsData?.page_size || 20,
              showSizeChanger: true,
            }}
            scroll={{ x: 1000 }}
          />
        </TabPane>
      </Tabs>

      {/* 规则编辑弹窗 */}
      <Modal
        title={editingRule ? '编辑风控规则' : '新增风控规则'}
        open={ruleModalVisible}
        onCancel={() => setRuleModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={saveRuleMutation.isPending}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSaveRule}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="规则名称"
                name="rule_name"
                rules={[{ required: true, message: '请输入规则名称' }]}
              >
                <Input placeholder="例如：单股持仓上限" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="规则类型"
                name="rule_type"
                rules={[{ required: true, message: '请选择规则类型' }]}
              >
                <Select placeholder="选择规则类型">
                  <Option value="SinglePositionLimit">单只持仓限制</Option>
                  <Option value="TotalPositionLimit">总仓位限制</Option>
                  <Option value="StopLossRule">止损规则</Option>
                  <Option value="IndustryConcentration">行业集中度</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="风控等级"
                name="level"
                rules={[{ required: true, message: '请选择风控等级' }]}
              >
                <Select placeholder="选择等级">
                  <Option value="info">提示（仅记录）</Option>
                  <Option value="warning">警告（提醒）</Option>
                  <Option value="block">阻断（阻止下单）</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="状态"
                name="enabled"
                valuePropName="checked"
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="规则参数（JSON 格式）"
            name="params"
          >
            <TextArea
              rows={6}
              placeholder='{"max_pct": 0.15, "cash": 1000000}'
            />
          </Form.Item>

          <Form.Item
            label="规则描述"
            name="description"
          >
            <TextArea rows={3} placeholder="简要描述此风控规则的作用" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
