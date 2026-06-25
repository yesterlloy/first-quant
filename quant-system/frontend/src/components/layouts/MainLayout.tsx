import { useState } from 'react';
import { Avatar, Button, Dropdown, Layout, Menu, Space, Typography, theme } from 'antd';
import type { MenuProps } from 'antd';
import {
  DatabaseOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  LineChartOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  RocketOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useUserStore } from '../../stores/useUserStore';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

/** 侧边栏菜单项 */
const menuItems: MenuProps['items'] = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '数据看板' },
  { key: '/factor', icon: <ExperimentOutlined />, label: '因子分析' },
  { key: '/backtest', icon: <LineChartOutlined />, label: '策略回测' },
  { key: '/ml', icon: <ThunderboltOutlined />, label: 'ML模型' },
  { key: '/trading', icon: <RocketOutlined />, label: '实盘监控' },
  { key: '/risk', icon: <SafetyOutlined />, label: '风控中心' },
];

/**
 * 主布局：左侧导航 + 顶部用户区 + 内容出口（Outlet）
 */
export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useUserStore();
  const { token } = theme.useToken();

  // 侧边栏菜单点击跳转
  const onMenuClick: MenuProps['onClick'] = ({ key }) => {
    navigate(key);
  };

  // 用户下拉菜单
  const userMenuItems: MenuProps['items'] = [
    { key: 'profile', icon: <UserOutlined />, label: '个人信息' },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
  ];

  const onUserMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') {
      logout();
      navigate('/login', { replace: true });
    }
  };

  // 选中态：取一级路径段
  const selectedKey = `/${location.pathname.split('/')[1] || 'dashboard'}`;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="dark" width={220}>
        {/* Logo 区 */}
        <div
          style={{
            height: 60,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
          }}
        >
          <Title level={4} style={{ color: '#fff', margin: 0 }}>
            {collapsed ? 'Q' : '量化系统'}
          </Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={onMenuClick}
        />
      </Sider>

      <Layout>
        <Header
          style={{
            background: token.colorBgContainer,
            padding: '0 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Button
            type="text"
            onClick={() => setCollapsed((c) => !c)}
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          />
          <Dropdown menu={{ items: userMenuItems, onClick: onUserMenuClick }} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} />
              <Text>{user?.full_name || user?.username || '用户'}</Text>
            </Space>
          </Dropdown>
        </Header>

        <Content style={{ margin: 0, minHeight: 280, overflow: 'auto' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
