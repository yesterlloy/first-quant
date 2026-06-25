import { useState } from 'react';
import { App, Button, Card, Form, Input, Typography } from 'antd';
import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { login } from '../../services/auth';
import { useUserStore } from '../../stores/useUserStore';

const { Title, Text } = Typography;

interface LoginForm {
  username: string;
  password: string;
}

/**
 * 登录页：表单提交调用 /auth/login（OAuth2 表单），成功后写入状态并跳转看板。
 */
export default function Login() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setAuth = useUserStore((s) => s.setAuth);
  const { message } = App.useApp();

  const onFinish = async (values: LoginForm) => {
    setLoading(true);
    try {
      const { access_token, user } = await login(values.username, values.password);
      setAuth(access_token, user);
      message.success(`欢迎回来，${user.full_name || user.username}`);
      navigate('/dashboard', { replace: true });
    } catch {
      // 错误信息已由 axios 拦截器统一提示，此处无需重复处理
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
      }}
    >
      <Card style={{ width: 400, boxShadow: '0 8px 24px rgba(0,0,0,0.15)' }} bordered={false}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={2} style={{ marginBottom: 4 }}>
            量化系统
          </Title>
          <Text type="secondary">A股因子选股量化平台</Text>
        </div>

        <Form
          name="login"
          size="large"
          initialValues={{ remember: true }}
          onFinish={onFinish}
          autoComplete="off"
        >
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" autoComplete="username" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              autoComplete="current-password"
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
