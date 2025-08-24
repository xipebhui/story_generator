import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Form,
  Input,
  InputNumber,
  Radio,
  Switch,
  Button,
  Card,
  Space,
  message,
  Typography,
} from 'antd';
import {
  VideoCameraOutlined,
  UserOutlined,
  ClockCircleOutlined,
  PictureOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import pipelineService from '@/services/pipeline';
import { PipelineRequest, Gender } from '@/types/task';

const { Title, Paragraph } = Typography;

const CreateTask: React.FC = () => {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: any) => {
    try {
      setLoading(true);
      
      const request: PipelineRequest = {
        video_id: values.video_id,
        creator_id: values.creator_id,
        gender: values.gender,
        duration: values.duration,
        image_dir: values.image_dir,
        export_video: values.export_video || false,
      };

      const response = await pipelineService.createTask(request);
      message.success('任务创建成功！');
      
      // 跳转到监控页面
      navigate(`/monitor/${response.task_id}`);
    } catch (error) {
      console.error('创建任务失败:', error);
      message.error('创建任务失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Title level={2}>
        <VideoCameraOutlined /> 新建视频任务
      </Title>
      <Paragraph type="secondary">
        输入YouTube视频ID和配置参数，系统将自动生成故事内容、语音和剪映草稿
      </Paragraph>

      <Card style={{ maxWidth: 800, margin: '0 auto' }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            gender: Gender.Female,
            duration: 60,
            export_video: false,
          }}
        >
          <Form.Item
            label={
              <span>
                <VideoCameraOutlined /> 视频ID
              </span>
            }
            name="video_id"
            rules={[
              { required: true, message: '请输入YouTube视频ID' },
              { 
                pattern: /^[a-zA-Z0-9_-]{11}$/,
                message: '请输入有效的YouTube视频ID（11位字符）'
              },
            ]}
            tooltip="YouTube视频URL中v=后面的11位字符"
          >
            <Input placeholder="例如：dQw4w9WgXcQ" />
          </Form.Item>

          <Form.Item
            label={
              <span>
                <UserOutlined /> 创作者ID
              </span>
            }
            name="creator_id"
            rules={[{ required: true, message: '请输入创作者ID' }]}
          >
            <Input placeholder="例如：user_001" />
          </Form.Item>

          <Form.Item
            label="语音性别"
            name="gender"
            rules={[{ required: true }]}
          >
            <Radio.Group>
              <Radio value={Gender.Male}>男声</Radio>
              <Radio value={Gender.Female}>女声</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item
            label={
              <span>
                <ClockCircleOutlined /> 视频时长（秒）
              </span>
            }
            name="duration"
            rules={[
              { required: true, message: '请输入视频时长' },
              { type: 'number', min: 30, max: 300, message: '时长应在30-300秒之间' },
            ]}
          >
            <InputNumber
              min={30}
              max={300}
              step={10}
              style={{ width: '100%' }}
              placeholder="建议60秒"
            />
          </Form.Item>

          <Form.Item
            label={
              <span>
                <PictureOutlined /> 图片库目录
              </span>
            }
            name="image_dir"
            tooltip="可选，指定图片素材目录"
          >
            <Input placeholder="例如：/path/to/images（可选）" />
          </Form.Item>

          <Form.Item
            name="export_video"
            valuePropName="checked"
          >
            <Space>
              <Switch />
              <span>
                <RocketOutlined /> 自动导出视频（需要额外时间）
              </span>
            </Space>
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading} size="large">
                开始创作
              </Button>
              <Button size="large" onClick={() => form.resetFields()}>
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default CreateTask;