import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  Button,
  Space,
  Typography,
  Tag,
  InputNumber,
  Upload,
  message,
  Alert,
} from 'antd';
import {
  RocketOutlined,
  PlusOutlined,
  UploadOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import pipelineService from '@/services/pipeline';
import { PublishRequest } from '@/types/task';

const { Title, Paragraph, TextArea } = Typography;

const PublishPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [tags, setTags] = useState<string[]>([]);
  const [inputTag, setInputTag] = useState('');

  // 添加标签
  const handleAddTag = () => {
    if (inputTag && !tags.includes(inputTag)) {
      setTags([...tags, inputTag]);
      setInputTag('');
    }
  };

  // 删除标签
  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter(t => t !== tag));
  };

  // 提交发布
  const handleSubmit = async (values: any) => {
    if (!taskId) {
      message.error('任务ID不存在');
      return;
    }

    try {
      setLoading(true);
      
      const request: PublishRequest = {
        task_id: taskId,
        video_path: values.video_path || '',
        title: values.title,
        description: values.description,
        tags: tags,
        thumbnail_path: values.thumbnail_path,
        publish_time: values.publish_time,
      };

      const response = await pipelineService.publishVideo(request);
      
      if (response.success === false) {
        message.warning(response.message || '发布功能尚未实现');
      } else {
        message.success('视频发布成功！');
        navigate('/publish/history');
      }
    } catch (error) {
      console.error('发布失败:', error);
      message.error('发布失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Title level={2}>
        <RocketOutlined /> 发布视频
      </Title>
      <Paragraph type="secondary">
        编辑视频信息并发布到平台（功能开发中）
      </Paragraph>

      <Alert
        message="提示"
        description="发布功能正在开发中，当前仅作为界面预览"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Card style={{ maxWidth: 800, margin: '0 auto' }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            publish_time: 0,
          }}
        >
          <Form.Item
            label="视频标题"
            name="title"
            rules={[{ required: true, message: '请输入视频标题' }]}
          >
            <Input placeholder="输入吸引人的标题" maxLength={100} showCount />
          </Form.Item>

          <Form.Item
            label="视频描述"
            name="description"
            rules={[{ required: true, message: '请输入视频描述' }]}
          >
            <TextArea
              placeholder="详细描述视频内容"
              rows={6}
              maxLength={5000}
              showCount
            />
          </Form.Item>

          <Form.Item label="标签">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                <Input
                  placeholder="输入标签"
                  value={inputTag}
                  onChange={(e) => setInputTag(e.target.value)}
                  onPressEnter={handleAddTag}
                  style={{ width: 200 }}
                />
                <Button icon={<PlusOutlined />} onClick={handleAddTag}>
                  添加
                </Button>
              </Space>
              <Space wrap>
                {tags.map(tag => (
                  <Tag
                    key={tag}
                    closable
                    onClose={() => handleRemoveTag(tag)}
                    color="blue"
                  >
                    {tag}
                  </Tag>
                ))}
              </Space>
            </Space>
          </Form.Item>

          <Form.Item
            label="封面图片"
            name="thumbnail_path"
          >
            <Upload
              name="thumbnail"
              listType="picture-card"
              maxCount={1}
              beforeUpload={() => {
                message.info('上传功能尚未实现');
                return false;
              }}
            >
              <div>
                <UploadOutlined />
                <div style={{ marginTop: 8 }}>上传封面</div>
              </div>
            </Upload>
          </Form.Item>

          <Form.Item
            label={
              <span>
                <ClockCircleOutlined /> 发布时间（延迟分钟数）
              </span>
            }
            name="publish_time"
            tooltip="0表示立即发布，其他数值表示延迟的分钟数"
          >
            <InputNumber
              min={0}
              max={10080}
              step={30}
              style={{ width: '100%' }}
              placeholder="0表示立即发布"
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading} size="large">
                确认发布
              </Button>
              <Button size="large" onClick={() => navigate(-1)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default PublishPage;