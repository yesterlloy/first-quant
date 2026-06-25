import { Typography, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

const { Title } = Typography;

interface DashboardHeaderProps {
  onRefresh: () => void;
}

/**
 * 页面头部组件
 */
export function DashboardHeader({ onRefresh }: DashboardHeaderProps) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
      <Title level={3} style={{ margin: 0 }}>
        📊 数据看板
      </Title>
      <Button icon={<ReloadOutlined />} onClick={onRefresh}>
        刷新数据
      </Button>
    </div>
  );
}
