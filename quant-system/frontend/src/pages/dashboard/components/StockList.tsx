import { Card, Input, Table, Spin, Button, Typography } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import type { StockInfo } from '../../../types/data';

const { Text } = Typography;

interface StockListProps {
  searchKeyword: string;
  onSearchChange: (keyword: string) => void;
  stockData?: {
    items: StockInfo[];
    total: number;
    page_size: number;
    page: number;
  };
  loading?: boolean;
  onSelectStock: (code: string) => void;
}

/**
 * 股票列表组件
 */
export function StockList({
  searchKeyword,
  onSearchChange,
  stockData,
  loading = false,
  onSelectStock,
}: StockListProps) {
  const columns = [
    {
      title: '股票代码',
      dataIndex: 'code',
      key: 'code',
      width: 100,
      render: (code: string) => <Text strong>{code}</Text>,
    },
    {
      title: '股票名称',
      dataIndex: 'name',
      key: 'name',
      width: 120,
    },
    {
      title: '行业',
      dataIndex: 'industry',
      key: 'industry',
      width: 100,
      render: (v: string) => v || '-',
    },
    {
      title: '上市日期',
      dataIndex: 'list_date',
      key: 'list_date',
      width: 120,
      render: (v: string) => v || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: StockInfo) => (
        <Button type="link" size="small" onClick={() => onSelectStock(record.code)}>
          查看K线
        </Button>
      ),
    },
  ];

  return (
    <Card
      title="📋 股票列表"
      extra={
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索股票代码/名称"
          style={{ width: 250 }}
          value={searchKeyword}
          onChange={(e) => onSearchChange(e.target.value)}
          allowClear
        />
      }
    >
      <Spin spinning={loading}>
        <Table
          columns={columns}
          dataSource={stockData?.items || []}
          rowKey="code"
          pagination={{
            total: stockData?.total || 0,
            pageSize: stockData?.page_size || 20,
            current: stockData?.page || 1,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 只`,
          }}
          scroll={{ y: 400 }}
        />
      </Spin>
    </Card>
  );
}
