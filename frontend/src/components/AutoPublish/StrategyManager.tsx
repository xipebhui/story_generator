import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  message,
  Space,
  Tag,
  Tooltip,
  Drawer,
  Descriptions,
  Progress,
  Statistic,
  Row,
  Col,
  Alert
} from 'antd';
import {
  PlusOutlined,
  ExperimentOutlined,
  BarChartOutlined,
  TrophyOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { autoPublishService } from '../../services/autoPublish';
import dayjs from 'dayjs';

interface Strategy {
  strategy_id: string;
  strategy_name: string;
  strategy_type: string;
  parameters: any;
  description?: string;
  is_active: boolean;
  start_date?: string;
  end_date?: string;
  created_at: string;
}

const StrategyManager: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [reportVisible, setReportVisible] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [strategyReport, setStrategyReport] = useState<any>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadStrategies();
  }, []);

  const loadStrategies = async () => {
    setLoading(true);
    try {
      const response = await autoPublishService.listStrategies();
      const data = response?.strategies || response || [];
      setStrategies(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('加载策略失败:', error);
      message.error('加载策略失败');
      setStrategies([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    form.resetFields();
    setModalVisible(true);
  };

  const handleSubmit = async (values: any) => {
    try {
      // 构建策略参数
      const parameters: any = {};
      if (values.strategy_type === 'ab_test') {
        parameters.variants = values.variants?.split(',') || ['control', 'variant_a'];
        parameters.metric = values.metric || 'views';
      } else if (values.strategy_type === 'weighted') {
        parameters.weights = values.weights?.split(',').map(Number) || [1, 1];
      }

      await autoPublishService.createStrategy({
        strategy_name: values.strategy_name,
        strategy_type: values.strategy_type,
        parameters,
        description: values.description,
        start_date: values.start_date?.format('YYYY-MM-DD'),
        end_date: values.end_date?.format('YYYY-MM-DD')
      });

      message.success('创建策略成功');
      setModalVisible(false);
      loadStrategies();
    } catch (error) {
      message.error('创建策略失败');
    }
  };

  const showReport = async (strategy: Strategy) => {
    setSelectedStrategy(strategy);
    setReportVisible(true);
    
    try {
      const report = await autoPublishService.getStrategyReport(strategy.strategy_id);
      setStrategyReport(report);
    } catch (error) {
      message.error('加载策略报告失败');
    }
  };

  const columns = [
    {
      title: '策略名称',
      dataIndex: 'strategy_name',
      key: 'strategy_name',
      render: (text: string, record: Strategy) => (
        <Space>
          <ExperimentOutlined />
          <a onClick={() => showReport(record)}>{text}</a>
        </Space>
      )
    },
    {
      title: '类型',
      dataIndex: 'strategy_type',
      key: 'strategy_type',
      width: 120,
      render: (type: string) => {
        const typeMap = {
          ab_test: { text: 'A/B测试', color: 'blue' },
          round_robin: { text: '轮流', color: 'green' },
          weighted: { text: '加权', color: 'orange' },
          random: { text: '随机', color: 'purple' }
        };
        const config = typeMap[type as keyof typeof typeMap];
        return <Tag color={config?.color}>{config?.text}</Tag>;
      }
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: '生效时间',
      key: 'period',
      width: 200,
      render: (_: any, record: Strategy) => {
        if (!record.start_date && !record.end_date) {
          return <Tag>永久生效</Tag>;
        }
        return (
          <Space direction="vertical" size={0}>
            {record.start_date && <span>开始: {record.start_date}</span>}
            {record.end_date && <span>结束: {record.end_date}</span>}
          </Space>
        );
      }
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'default'}>
          {active ? '活跃' : '停用'}
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: Strategy) => (
        <Space>
          <Tooltip title="查看报告">
            <Button
              icon={<BarChartOutlined />}
              size="small"
              onClick={() => showReport(record)}
            />
          </Tooltip>
        </Space>
      )
    }
  ];

  return (
    <>
      <Card
        title="策略管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            创建策略
          </Button>
        }
      >
        <Alert
          message="策略说明"
          description="通过创建不同的策略，可以对账号组进行A/B测试、轮流发布等操作，并通过数据分析找出最优策略。"
          type="info"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
        
        <Table
          columns={columns}
          dataSource={strategies}
          rowKey="strategy_id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个策略`
          }}
        />
      </Card>

      <Modal
        title="创建策略"
        visible={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        width={600}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="strategy_name"
            label="策略名称"
            rules={[{ required: true, message: '请输入策略名称' }]}
          >
            <Input placeholder="例如：标题优化A/B测试" />
          </Form.Item>

          <Form.Item
            name="strategy_type"
            label="策略类型"
            rules={[{ required: true, message: '请选择策略类型' }]}
            initialValue="ab_test"
          >
            <Select>
              <Select.Option value="ab_test">A/B测试</Select.Option>
              <Select.Option value="round_robin">轮流分配</Select.Option>
              <Select.Option value="weighted">加权分配</Select.Option>
              <Select.Option value="random">随机分配</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) =>
              prevValues.strategy_type !== currentValues.strategy_type
            }
          >
            {({ getFieldValue }) =>
              getFieldValue('strategy_type') === 'ab_test' ? (
                <>
                  <Form.Item
                    name="variants"
                    label="变体名称"
                    help="用逗号分隔，例如：control,variant_a,variant_b"
                  >
                    <Input placeholder="control,variant_a" />
                  </Form.Item>
                  <Form.Item
                    name="metric"
                    label="评估指标"
                  >
                    <Select defaultValue="views">
                      <Select.Option value="views">观看量</Select.Option>
                      <Select.Option value="engagement_rate">互动率</Select.Option>
                      <Select.Option value="ctr">点击率</Select.Option>
                    </Select>
                  </Form.Item>
                </>
              ) : getFieldValue('strategy_type') === 'weighted' ? (
                <Form.Item
                  name="weights"
                  label="权重配置"
                  help="用逗号分隔，例如：1,2,1"
                >
                  <Input placeholder="1,1,1" />
                </Form.Item>
              ) : null
            }
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea rows={2} placeholder="描述策略的目的和预期效果" />
          </Form.Item>

          <Form.Item
            name="start_date"
            label="开始日期"
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="end_date"
            label="结束日期"
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title="策略报告"
        placement="right"
        width={800}
        visible={reportVisible}
        onClose={() => setReportVisible(false)}
      >
        {selectedStrategy && strategyReport && (
          <>
            <Descriptions bordered column={1} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="策略名称">
                {selectedStrategy.strategy_name}
              </Descriptions.Item>
              <Descriptions.Item label="策略类型">
                <Tag>{selectedStrategy.strategy_type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {new Date(selectedStrategy.created_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            {strategyReport.summary && (
              <Alert
                message="分析结论"
                description={strategyReport.summary}
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            {strategyReport.analyses?.views?.variants && (
              <Card title="观看量分析" style={{ marginBottom: 16 }}>
                <Row gutter={16}>
                  {Object.entries(strategyReport.analyses.views.variants).map(([variant, stats]: [string, any]) => (
                    <Col span={12} key={variant}>
                      <Card>
                        <Statistic
                          title={variant}
                          value={stats.mean?.toFixed(0) || 0}
                          prefix={variant === strategyReport.analyses.views.winner ? <TrophyOutlined style={{ color: '#faad14' }} /> : null}
                        />
                        <Space direction="vertical" size={0} style={{ marginTop: 8 }}>
                          <span>样本数: {stats.count}</span>
                          <span>标准差: {stats.std?.toFixed(2) || 0}</span>
                          <span>最小值: {stats.min}</span>
                          <span>最大值: {stats.max}</span>
                        </Space>
                      </Card>
                    </Col>
                  ))}
                </Row>

                {strategyReport.analyses.views.statistical_test && (
                  <Alert
                    message={`统计检验结果`}
                    description={
                      <Space direction="vertical">
                        <span>P值: {strategyReport.analyses.views.statistical_test.p_value?.toFixed(4)}</span>
                        <span>
                          结果: {strategyReport.analyses.views.statistical_test.significant ? 
                            '存在显著差异' : '无显著差异'}
                        </span>
                        {strategyReport.analyses.views.improvement && (
                          <span>提升幅度: {strategyReport.analyses.views.improvement.toFixed(1)}%</span>
                        )}
                      </Space>
                    }
                    type={strategyReport.analyses.views.statistical_test.significant ? 'success' : 'warning'}
                    style={{ marginTop: 16 }}
                  />
                )}
              </Card>
            )}

            {strategyReport.recommendations && (
              <Card title="建议">
                <ul>
                  {strategyReport.recommendations.map((rec: string, index: number) => (
                    <li key={index}>{rec}</li>
                  ))}
                </ul>
              </Card>
            )}
          </>
        )}
      </Drawer>
    </>
  );
};

export default StrategyManager;