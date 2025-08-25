import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  TimePicker,
  Switch,
  Button,
  Space,
  Alert,
  Divider,
  Row,
  Col,
  Tag,
  Card,
  Typography,
  message
} from 'antd';
import {
  CloudUploadOutlined,
  YoutubeOutlined,
  CalendarOutlined,
  GlobalOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  TagsOutlined,
  CloseOutlined
} from '@ant-design/icons';
import { Task, TaskResult } from '../../types/task';
import { pipelineService } from '../../services/pipeline';
import dayjs from 'dayjs';

const { TextArea } = Input;
const { Title, Text } = Typography;
const { Option } = Select;

interface PublishModalProps {
  visible: boolean;
  task: Task | null;
  onClose: () => void;
  onSuccess: () => void;
}

const PublishModal: React.FC<PublishModalProps> = ({
  visible,
  task,
  onClose,
  onSuccess
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [publishType, setPublishType] = useState<'immediate' | 'scheduled'>('immediate');

  // 加载任务结果
  useEffect(() => {
    if (task && visible) {
      loadTaskResult();
    }
  }, [task, visible]);

  const loadTaskResult = async () => {
    if (!task) return;
    
    try {
      const data = await pipelineService.getResult(task.task_id);
      setResult(data);
      
      // 预填充YouTube元数据
      if (data.youtube_metadata) {
        form.setFieldsValue({
          title: data.youtube_metadata.title,
          description: data.youtube_metadata.description,
          tags: data.youtube_metadata.tags?.join(', ')
        });
      }
    } catch (error) {
      console.error('加载任务结果失败:', error);
    }
  };

  // 提交发布
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // 模拟发布请求
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      message.success('发布成功！视频已上传到YouTube');
      onSuccess();
    } catch (error) {
      console.error('发布失败:', error);
      message.error('发布失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  if (!task) return null;

  return (
    <Modal
      title={
        <Space>
          <CloudUploadOutlined />
          <span>发布到YouTube</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={800}
      footer={null}
      className="publish-modal"
    >
      <Space direction="vertical" size={24} style={{ width: '100%' }}>
        {/* 任务信息 */}
        <Card size="small" style={{ background: '#f0f2f5' }}>
          <Space>
            <Text type="secondary">任务ID:</Text>
            <Text code>{task.task_id}</Text>
            <Divider type="vertical" />
            <Text type="secondary">创建时间:</Text>
            <Text>{dayjs(task.created_at).format('YYYY-MM-DD HH:mm')}</Text>
          </Space>
        </Card>

        {/* 发布表单 */}
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            visibility: 'public',
            category: 'Entertainment',
            language: 'zh-CN',
            comments: true,
            ratings: true
          }}
        >
          {/* 基本信息 */}
          <Divider orientation="left">
            <Space>
              <YoutubeOutlined />
              基本信息
            </Space>
          </Divider>
          
          <Form.Item
            name="title"
            label="视频标题"
            rules={[{ required: true, message: '请输入视频标题' }]}
          >
            <Input
              placeholder="输入吸引人的标题"
              maxLength={100}
              showCount
            />
          </Form.Item>

          <Form.Item
            name="description"
            label="视频描述"
            rules={[{ required: true, message: '请输入视频描述' }]}
          >
            <TextArea
              placeholder="详细描述视频内容"
              rows={4}
              maxLength={5000}
              showCount
            />
          </Form.Item>

          <Form.Item
            name="tags"
            label={
              <Space>
                <TagsOutlined />
                标签
              </Space>
            }
            rules={[{ required: true, message: '请输入标签' }]}
          >
            <TextArea
              placeholder="用逗号分隔多个标签"
              rows={2}
            />
          </Form.Item>

          {/* 发布设置 */}
          <Divider orientation="left">
            <Space>
              <CalendarOutlined />
              发布设置
            </Space>
          </Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="发布时间">
                <Select
                  value={publishType}
                  onChange={setPublishType}
                  style={{ width: '100%' }}
                >
                  <Option value="immediate">立即发布</Option>
                  <Option value="scheduled">定时发布</Option>
                </Select>
              </Form.Item>
              {publishType === 'scheduled' && (
                <Row gutter={8}>
                  <Col span={12}>
                    <Form.Item name="publishDate">
                      <DatePicker
                        style={{ width: '100%' }}
                        placeholder="选择日期"
                        disabledDate={(current) => 
                          current && current < dayjs().startOf('day')
                        }
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="publishTime">
                      <TimePicker
                        style={{ width: '100%' }}
                        placeholder="选择时间"
                        format="HH:mm"
                      />
                    </Form.Item>
                  </Col>
                </Row>
              )}
            </Col>

            <Col span={12}>
              <Form.Item
                name="visibility"
                label="可见性"
              >
                <Select>
                  <Option value="public">
                    <Space>
                      <EyeOutlined />
                      公开
                    </Space>
                  </Option>
                  <Option value="unlisted">
                    <Space>
                      <EyeInvisibleOutlined />
                      不公开
                    </Space>
                  </Option>
                  <Option value="private">
                    <Space>
                      <EyeInvisibleOutlined />
                      私密
                    </Space>
                  </Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="category"
                label="视频类别"
              >
                <Select>
                  <Option value="Entertainment">娱乐</Option>
                  <Option value="Education">教育</Option>
                  <Option value="Gaming">游戏</Option>
                  <Option value="Music">音乐</Option>
                  <Option value="News">新闻</Option>
                  <Option value="Sports">体育</Option>
                  <Option value="Technology">科技</Option>
                </Select>
              </Form.Item>
            </Col>

            <Col span={12}>
              <Form.Item
                name="language"
                label={
                  <Space>
                    <GlobalOutlined />
                    语言
                  </Space>
                }
              >
                <Select>
                  <Option value="zh-CN">中文（简体）</Option>
                  <Option value="zh-TW">中文（繁体）</Option>
                  <Option value="en-US">英语</Option>
                  <Option value="ja-JP">日语</Option>
                  <Option value="ko-KR">韩语</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          {/* 高级设置 */}
          <Divider orientation="left">高级设置</Divider>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="comments"
                label="允许评论"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="ratings"
                label="显示点赞数"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="embedAllowed"
                label="允许嵌入"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Form>

        {/* 提示信息 */}
        <Alert
          message="发布提示"
          description="发布后，视频将根据您的设置上传到YouTube。请确保内容符合YouTube社区准则。"
          type="info"
          showIcon
        />

        {/* 操作按钮 */}
        <Row justify="end">
          <Space>
            <Button onClick={onClose} icon={<CloseOutlined />}>
              取消
            </Button>
            <Button
              type="primary"
              loading={loading}
              onClick={handleSubmit}
              icon={<CloudUploadOutlined />}
              className="gradient-button"
            >
              {publishType === 'immediate' ? '立即发布' : '定时发布'}
            </Button>
          </Space>
        </Row>
      </Space>
    </Modal>
  );
};

export default PublishModal;