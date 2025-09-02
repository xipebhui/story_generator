import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  InputNumber,
  Upload,
  Button,
  Space,
  Alert,
  Divider,
  Row,
  Col,
  message,
  Spin,
  Avatar,
  Tag,
  Tooltip
} from 'antd';
import {
  CloudUploadOutlined,
  UserOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  PictureOutlined,
  CloseOutlined,
  InfoCircleOutlined,
  VideoCameraOutlined,
  ThunderboltOutlined,
  ApiOutlined
} from '@ant-design/icons';
import { Task, TaskResult } from '../../types/task';
import { Account } from '../../types/account';
import { pipelineAdapter } from '../../services/pipelineAdapter';
import { accountService } from '../../services/account';
import { backendAccountService } from '../../services/backend';
import dayjs from 'dayjs';
import type { UploadFile } from 'antd/es/upload/interface';

const { TextArea } = Input;
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
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [publishMode, setPublishMode] = useState<'immediate' | 'scheduled' | 'interval'>('immediate');
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [thumbnailPath, setThumbnailPath] = useState<string | null>(null); // 存储上传后的缩略图路径
  const [ytEngineStatus, setYtEngineStatus] = useState<{ available: boolean; message: string } | null>(null);
  const [titleOptions, setTitleOptions] = useState<string[]>([]);

  // 加载账号列表和YTEngine状态
  useEffect(() => {
    if (visible) {
      loadAccounts();
      checkYTEngineStatus();
    }
  }, [visible]);

  // 加载任务结果
  useEffect(() => {
    if (task && visible) {
      loadTaskResult();
    }
  }, [task, visible]);

  const loadAccounts = async () => {
    setLoadingAccounts(true);
    try {
      // 优先使用后端真实账号
      const backendAccounts = await backendAccountService.getAccounts();
      
      // 转换为前端账号格式
      const formattedAccounts = backendAccounts.map((acc: any) => ({
        id: acc.account_id,
        name: acc.account_name,
        display_name: acc.display_name, // 添加display_name字段
        youtube_account: acc.account_name, // 使用 account_name 作为 youtube_account
        youtube_channel_id: acc.channel_url || '', // 使用 channel_url 或空字符串
        bitbrowser_name: acc.profile_id || acc.account_id, // 使用 profile_id 或 account_id
        status: acc.is_active ? 'active' : 'inactive' // 使用 is_active 字段
      }));
      
      setAccounts(formattedAccounts.filter(acc => acc.status === 'active'));
    } catch (error) {
      console.warn('无法加载后端账号，使用本地模拟账号');
      // 如果后端不可用，回退到本地模拟账号
      try {
        const data = await accountService.getAccounts();
        setAccounts(data.filter(acc => acc.status === 'active'));
      } catch (localError) {
        message.error('加载账号列表失败');
      }
    } finally {
      setLoadingAccounts(false);
    }
  };

  // 检查YTEngine服务状态
  const checkYTEngineStatus = async () => {
    try {
      const { ytEngineService } = await import('../../services/ytengine');
      const status = await ytEngineService.checkServiceStatus();
      setYtEngineStatus(status);
    } catch (error) {
      setYtEngineStatus({ available: false, message: 'YTEngine服务不可用' });
    }
  };

  const loadTaskResult = async () => {
    if (!task) return;
    
    try {
      const data = await pipelineAdapter.getResult(task.task_id);
      if (!data) {
        console.error('无法获取任务结果');
        return;
      }
      
      setResult(data);
      
      const metadata = data.youtube_metadata as any;
      if (metadata && metadata.titles && metadata.descriptions) {
        // 设置标题选项
        const englishTitles = metadata.titles.english || [];
        setTitleOptions(englishTitles);
        
        // 预填充表单
        form.setFieldsValue({
          title: englishTitles.length > 0 ? [englishTitles[0]] : [], // Select mode="tags"需要数组
          description: metadata.descriptions.english || '',
          video_path: data.video_path || data.draft_path || '',
          tags: metadata.tags?.english ? metadata.tags.english.join(', ') : ''
        });
      }
    } catch (error) {
      console.error('加载任务结果失败:', error);
    }
  };

  // 处理封面上传
  const handleThumbnailUpload = (info: any) => {
    setFileList(info.fileList);
  };

  const uploadProps = {
    name: 'thumbnail',
    listType: 'picture-card' as const,
    maxCount: 1,
    accept: 'image/jpeg,image/png,image/webp',
    beforeUpload: (file: File) => {
      const isImage = ['image/jpeg', 'image/png', 'image/webp'].includes(file.type);
      if (!isImage) {
        message.error('只支持 JPEG, PNG 或 WebP 格式的图片！');
        return false;
      }
      const isLt2M = file.size / 1024 / 1024 < 2;
      if (!isLt2M) {
        message.error('图片大小不能超过2MB！');
        return false;
      }
      return false; // 阻止自动上传
    },
    onRemove: () => {
      setFileList([]);
      setThumbnailPath(null); // 清除已上传的路径
    }
  };

  // 提交发布
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // 处理标题 - 如果是数组则取第一个
      const title = Array.isArray(values.title) ? values.title[0] : values.title;
      
      // 如果有封面图，先上传封面图
      let uploadedThumbnailPath = thumbnailPath;
      if (fileList.length > 0 && fileList[0].originFileObj) {
        try {
          message.loading('正在上传封面图...');
          const uploadResult = await backendAccountService.uploadThumbnail(
            task!.task_id,
            fileList[0].originFileObj as File
          );
          uploadedThumbnailPath = uploadResult.thumbnail_path;
          setThumbnailPath(uploadedThumbnailPath);
          message.success('封面图上传成功');
        } catch (error) {
          console.error('封面图上传失败:', error);
          message.warning('封面图上传失败，将继续发布视频');
        }
      }
      
      // 准备发布参数
      const publishParams: any = {
        task_id: task!.task_id,
        account_ids: [values.account_id],
        video_title: title,
        video_description: values.description,
        video_tags: values.tags?.split(',').map((t: string) => t.trim()).filter(Boolean),
        privacy_status: 'public',
        thumbnail_path: uploadedThumbnailPath || undefined
      };
      
      // 根据发布模式设置参数
      if (publishMode === 'scheduled' && values.publish_time) {
        publishParams.scheduled_time = values.publish_time.toISOString();
      } else if (publishMode === 'interval' && values.publish_interval) {
        // 将分钟转换为小时
        publishParams.publish_interval_hours = values.publish_interval / 60;
      }
      
      // 使用后端发布服务
      await backendAccountService.createPublish(publishParams);
      
      message.success('发布任务已创建！');
      onSuccess();
      form.resetFields();
      setFileList([]);
      setThumbnailPath(null);
    } catch (error: any) {
      console.error('发布失败:', error);
      message.error(error.message || '发布失败，请重试');
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
          <span>发布视频</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={800}
      footer={null}
      className="publish-modal"
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          publish_mode: 'immediate',
          category: 'Entertainment'
        }}
      >
        {/* 账号选择 */}
        <Form.Item
          name="account_id"
          label={
            <Space>
              <UserOutlined />
              选择发布账号
            </Space>
          }
          rules={[{ required: true, message: '请选择发布账号' }]}
        >
          <Select
            placeholder="请选择要发布到的账号"
            loading={loadingAccounts}
            notFoundContent={loadingAccounts ? <Spin size="small" /> : '暂无可用账号'}
          >
            {accounts.map(account => (
              <Option key={account.id} value={account.id}>
                {account.display_name || account.name}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Divider />

        {/* 视频信息 */}
        <Row gutter={16}>
          <Col span={24}>
            <Form.Item
              name="title"
              label="视频标题"
              rules={[{ required: true, message: '请选择或输入视频标题' }]}
            >
              {titleOptions.length > 0 ? (
                <Select
                  placeholder="选择一个标题或输入自定义标题"
                  mode="tags"
                  maxTagCount={1}
                  maxLength={100}
                >
                  {titleOptions.map((title, index) => (
                    <Option key={index} value={title}>
                      <Tooltip title={title}>
                        <span>{title.length > 50 ? title.substring(0, 50) + '...' : title}</span>
                      </Tooltip>
                    </Option>
                  ))}
                </Select>
              ) : (
                <Input
                  placeholder="输入吸引人的标题"
                  maxLength={100}
                  showCount
                />
              )}
            </Form.Item>
          </Col>
        </Row>

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

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="video_path"
              label="视频路径"
              rules={[{ required: true, message: '请输入视频路径' }]}
            >
              <Input
                placeholder="视频文件路径"
                prefix={<VideoCameraOutlined />}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="category"
              label="视频类别"
            >
              <Select placeholder="选择类别">
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
        </Row>

        {/* 封面上传 */}
        <Form.Item
          label={
            <Space>
              <PictureOutlined />
              上传封面
            </Space>
          }
        >
          <Upload
            {...uploadProps}
            fileList={fileList}
            onChange={handleThumbnailUpload}
          >
            {fileList.length === 0 && (
              <div>
                <PictureOutlined style={{ fontSize: 24, color: '#8c8c8c' }} />
                <div style={{ marginTop: 8, color: '#8c8c8c' }}>点击上传</div>
              </div>
            )}
          </Upload>
        </Form.Item>

        <Divider />

        {/* 发布时间设置 */}
        <Form.Item label="发布时间设置">
          <Select
            value={publishMode}
            onChange={setPublishMode}
            style={{ width: '100%' }}
          >
            <Option value="immediate">
              <Space>
                <ThunderboltOutlined />
                立即发布
              </Space>
            </Option>
            <Option value="scheduled">
              <Space>
                <CalendarOutlined />
                定时发布
              </Space>
            </Option>
            <Option value="interval">
              <Space>
                <ClockCircleOutlined />
                间隔发布
              </Space>
            </Option>
          </Select>
        </Form.Item>

        {publishMode === 'scheduled' && (
          <Form.Item
            name="publish_time"
            label="发布时间"
            rules={[{ required: true, message: '请选择发布时间' }]}
          >
            <DatePicker
              showTime
              style={{ width: '100%' }}
              placeholder="选择发布时间"
              disabledDate={(current) => 
                current && current < dayjs().startOf('minute')
              }
            />
          </Form.Item>
        )}

        {publishMode === 'interval' && (
          <Form.Item
            name="publish_interval"
            label="发布间隔（分钟）"
            rules={[{ required: true, message: '请输入发布间隔' }]}
          >
            <InputNumber
              min={5}
              max={1440}
              style={{ width: '100%' }}
              placeholder="最小5分钟，最大24小时"
            />
          </Form.Item>
        )}

        <Form.Item
          name="tags"
          label="标签（用逗号分隔）"
        >
          <TextArea
            placeholder="如：Education, Technology, Innovation"
            rows={2}
          />
        </Form.Item>

        {/* YTEngine状态提示 */}
        {ytEngineStatus && (
          <Alert
            message={
              <Space>
                <ApiOutlined />
                YTEngine服务状态
              </Space>
            }
            description={ytEngineStatus.message}
            type={ytEngineStatus.available ? 'success' : 'warning'}
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 发布提示 */}
        <Alert
          message="发布提示"
          description={
            <div>
              <div>• 请确保视频文件路径正确</div>
              <div>• 封面图片建议尺寸：1280x720px</div>
              <div>• 定时发布将在指定时间自动上传</div>
              <div>• 间隔发布可用于多账号错峰发布</div>
              {ytEngineStatus?.available && (
                <div style={{ marginTop: 8, color: '#52c41a' }}>
                  <ThunderboltOutlined /> 已连接到YTEngine，支持真实YouTube上传
                </div>
              )}
            </div>
          }
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
        />

        {/* 操作按钮 */}
        <Row justify="end" style={{ marginTop: 24 }}>
          <Space>
            <Button onClick={onClose} icon={<CloseOutlined />}>
              取消
            </Button>
            <Button
              type="primary"
              loading={loading}
              onClick={handleSubmit}
              icon={<CloudUploadOutlined />}
              className="btn btn-primary"
            >
              创建发布任务
            </Button>
          </Space>
        </Row>
      </Form>
    </Modal>
  );
};

export default PublishModal;