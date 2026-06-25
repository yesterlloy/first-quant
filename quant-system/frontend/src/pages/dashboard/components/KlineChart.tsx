import { useMemo } from 'react';
import { Row, Col, Card, Select, DatePicker, Space, Spin } from 'antd';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

interface QuoteItem {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  turnover?: number;
  change_pct?: number;
  turnover_rate?: number;
}

interface KlineChartProps {
  selectedStock: string;
  onStockChange: (code: string) => void;
  dateRange: [dayjs.Dayjs, dayjs.Dayjs];
  onDateRangeChange: (dates: [dayjs.Dayjs, dayjs.Dayjs]) => void;
  quotes?: QuoteItem[];
  loading?: boolean;
}

/**
 * K 线图组件
 */
export function KlineChart({
  selectedStock,
  onStockChange,
  dateRange,
  onDateRangeChange,
  quotes = [],
  loading = false,
}: KlineChartProps) {
  const klineOption: EChartsOption = useMemo(() => {
    if (!quotes || quotes.length === 0) {
      return {
        title: { text: '暂无数据' },
        tooltip: { trigger: 'axis' },
      };
    }

    // 按日期正序排列（后端返回的是倒序）
    const sortedQuotes = [...quotes].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    const dates = sortedQuotes.map((q) => q.date);
    const values = sortedQuotes.map((q) => [q.open, q.close, q.low, q.high]);
    const volumes = sortedQuotes.map((q) => q.volume);

    return {
      animation: false,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      grid: [
        { left: '10%', right: '8%', height: '50%' },
        { left: '10%', right: '8%', top: '63%', height: '16%' },
      ],
      xAxis: [
        { type: 'category', data: dates, scale: true, axisLine: { lineStyle: { color: '#8392A5' } } },
        { type: 'category', gridIndex: 1, data: dates, scale: true, axisLine: { lineStyle: { color: '#8392A5' } } },
      ],
      yAxis: [
        { scale: true, splitArea: { show: true }, axisLabel: { formatter: (v: number) => v.toFixed(2) } },
        { gridIndex: 1, scale: true, splitNumber: 2, axisLabel: { formatter: (v: number) => (v / 100000000).toFixed(1) + '亿' } },
      ],
      // 缩放和滑动条
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: Math.max(0, 100 - 50000 / dates.length),
          end: 100,
        },
        {
          type: 'slider',
          xAxisIndex: [0, 1],
          start: Math.max(0, 100 - 50000 / dates.length),
          end: 100,
          height: 20,
          bottom: '10%',
          borderColor: '#ccc',
          fillerColor: 'rgba(24, 144, 255, 0.2)',
          handleStyle: {
            color: '#1890ff',
          },
        },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: values,
          itemStyle: {
            color: '#cf1322', // 红涨
            color0: '#3f8600', // 绿跌
            borderColor: '#cf1322',
            borderColor0: '#3f8600',
          },
        },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes.map((v, i) => ({
            value: v,
            itemStyle: { color: sortedQuotes[i].close >= sortedQuotes[i].open ? '#cf1322' : '#3f8600' },
          })),
        },
      ],
    };
  }, [quotes]);

  const stockOptions = [
    { value: '000001', label: '000001 平安银行' },
    { value: '000002', label: '000002 万科A' },
    { value: '600519', label: '600519 贵州茅台' },
  ];

  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col span={24}>
        <Card
          title={`📈 K 线图 - ${selectedStock} ${quotes?.[0]?.close || ''}`}
          extra={
            <Space>
              <Select
                style={{ width: 180 }}
                value={selectedStock}
                onChange={onStockChange}
                placeholder="选择股票"
                showSearch
                optionFilterProp="label"
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={stockOptions}
              />
              <RangePicker
                value={dateRange}
                onChange={(dates) => dates && onDateRangeChange([dates[0]!, dates[1]!])}
              />
            </Space>
          }
        >
          <Spin spinning={loading}>
            <ReactECharts
              option={klineOption}
              style={{ height: 450, width: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </Spin>
        </Card>
      </Col>
    </Row>
  );
}
