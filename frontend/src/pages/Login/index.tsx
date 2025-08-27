import React, { useState } from 'react';
import { Form, Input, Button, Card, Tabs, message, Space } from 'antd';
import { UserOutlined, LockOutlined, KeyOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { authService } from '../../services/auth';
import './style.css';

const { TabPane } = Tabs;

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');
  const navigate = useNavigate();
  const [form] = Form.useForm();

  // 处理登录
  const handleLogin = async (values: any) => {
    setLoading(true);
    try {
      await authService.login(values.username, values.password);
      message.success('登录成功');
      navigate('/');
    } catch (error) {
      // 错误已在authService中处理
    } finally {
      setLoading(false);
    }
  };

  // 处理注册
  const handleRegister = async (values: any) => {
    setLoading(true);
    try {
      await authService.register(values.username, values.password, values.invite_code);
      message.success('注册成功');
      navigate('/');
    } catch (error) {
      // 错误已在authService中处理
    } finally {
      setLoading(false);
    }
  };

  // 切换标签时重置表单
  const handleTabChange = (key: string) => {
    setActiveTab(key as 'login' | 'register');
    form.resetFields();
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <Card className="login-card">
          <div className="login-header">
            <h1>YouTube Story Generator</h1>
            <p>AI驱动的视频创作平台</p>
          </div>
          
          <Tabs activeKey={activeTab} onChange={handleTabChange}>
            <TabPane tab="登录" key="login">
              <Form
                form={form}
                name="login"
                onFinish={handleLogin}
                autoComplete="off"
                layout="vertical"
              >
                <Form.Item
                  name="username"
                  rules={[{ required: true, message: '请输入用户名' }]}
                >
                  <Input
                    size="large"
                    prefix={<UserOutlined />}
                    placeholder="用户名"
                  />
                </Form.Item>

                <Form.Item
                  name="password"
                  rules={[{ required: true, message: '请输入密码' }]}
                >
                  <Input.Password
                    size="large"
                    prefix={<LockOutlined />}
                    placeholder="密码"
                  />
                </Form.Item>

                <Form.Item>
                  <Button
                    type="primary"
                    htmlType="submit"
                    size="large"
                    loading={loading}
                    block
                  >
                    登录
                  </Button>
                </Form.Item>
              </Form>
            </TabPane>

            <TabPane tab="注册" key="register">
              <Form
                form={form}
                name="register"
                onFinish={handleRegister}
                autoComplete="off"
                layout="vertical"
              >
                <Form.Item
                  name="username"
                  rules={[
                    { required: true, message: '请输入用户名' },
                    { min: 3, message: '用户名至少3个字符' },
                    { max: 20, message: '用户名最多20个字符' },
                    { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' }
                  ]}
                >
                  <Input
                    size="large"
                    prefix={<UserOutlined />}
                    placeholder="用户名"
                  />
                </Form.Item>

                <Form.Item
                  name="password"
                  rules={[
                    { required: true, message: '请输入密码' },
                    { min: 6, message: '密码至少6个字符' }
                  ]}
                >
                  <Input.Password
                    size="large"
                    prefix={<LockOutlined />}
                    placeholder="密码"
                  />
                </Form.Item>

                <Form.Item
                  name="confirmPassword"
                  dependencies={['password']}
                  rules={[
                    { required: true, message: '请确认密码' },
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        if (!value || getFieldValue('password') === value) {
                          return Promise.resolve();
                        }
                        return Promise.reject(new Error('两次输入的密码不一致'));
                      },
                    }),
                  ]}
                >
                  <Input.Password
                    size="large"
                    prefix={<LockOutlined />}
                    placeholder="确认密码"
                  />
                </Form.Item>

                <Form.Item
                  name="invite_code"
                  rules={[
                    { required: true, message: '请输入邀请码' }
                  ]}
                >
                  <Input
                    size="large"
                    prefix={<KeyOutlined />}
                    placeholder="邀请码"
                  />
                </Form.Item>

                <Form.Item>
                  <Button
                    type="primary"
                    htmlType="submit"
                    size="large"
                    loading={loading}
                    block
                  >
                    注册
                  </Button>
                </Form.Item>
              </Form>
            </TabPane>
          </Tabs>
        </Card>
      </div>
    </div>
  );
};

export default Login;