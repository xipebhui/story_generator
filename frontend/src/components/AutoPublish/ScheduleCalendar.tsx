import React, { useState, useEffect } from 'react';
import { Card, Calendar, Badge, Modal, List, Tag, Button, DatePicker, TimePicker, Select, message, Space, Tooltip } from 'antd';
import { CalendarOutlined, PlusOutlined, ClockCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { autoPublishService } from '../../services/autoPublish';

interface ScheduleSlot {
  slot_id: number;
  account_id: string;
  slot_time: string;
  status: string;
  task_id?: string;
}

const ScheduleCalendar: React.FC = () => {
  const [selectedDate, setSelectedDate] = useState<Dayjs>(dayjs());
  const [slots, setSlots] = useState<ScheduleSlot[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [generateModalVisible, setGenerateModalVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [configs, setConfigs] = useState<any[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<string>('');

  useEffect(() => {
    loadConfigs();
  }, []);

  useEffect(() => {
    if (selectedConfig) {
      loadSlots();
    }
  }, [selectedDate, selectedConfig]);

  const loadConfigs = async () => {
    try {
      const response = await autoPublishService.listPublishConfigs();
      const data = response?.configs || response || [];
      setConfigs(Array.isArray(data) ? data : []);
      if (data.length > 0) {
        setSelectedConfig(data[0].config_id);
      }
    } catch (error) {
      console.error('加载配置失败:', error);
      setConfigs([]);
      message.error('加载配置失败');
    }
  };

  const loadSlots = async () => {
    if (!selectedConfig) return;
    
    setLoading(true);
    try {
      const data = await autoPublishService.getScheduleSlots(
        selectedConfig,
        selectedDate.format('YYYY-MM-DD')
      );
      setSlots(data.slots || []);
    } catch (error) {
      console.error('加载调度槽位失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSlots = async (values: any) => {
    try {
      await autoPublishService.generateScheduleSlots({
        config_id: selectedConfig,
        target_date: values.date.format('YYYY-MM-DD'),
        start_hour: values.startTime.hour(),
        end_hour: values.endTime.hour(),
        strategy: values.strategy || 'even'
      });
      message.success('生成调度槽位成功');
      setGenerateModalVisible(false);
      loadSlots();
    } catch (error) {
      message.error('生成调度槽位失败');
    }
  };

  const dateCellRender = (date: Dayjs) => {
    const dateStr = date.format('YYYY-MM-DD');
    const daySlots = slots.filter(slot => 
      dayjs(slot.slot_time).format('YYYY-MM-DD') === dateStr
    );
    
    if (daySlots.length === 0) return null;
    
    const statusCounts = {
      pending: daySlots.filter(s => s.status === 'pending').length,
      scheduled: daySlots.filter(s => s.status === 'scheduled').length,
      completed: daySlots.filter(s => s.status === 'completed').length,
      failed: daySlots.filter(s => s.status === 'failed').length
    };

    return (
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {statusCounts.pending > 0 && (
          <li>
            <Badge status="warning" text={`待执行 ${statusCounts.pending}`} />
          </li>
        )}
        {statusCounts.scheduled > 0 && (
          <li>
            <Badge status="processing" text={`已调度 ${statusCounts.scheduled}`} />
          </li>
        )}
        {statusCounts.completed > 0 && (
          <li>
            <Badge status="success" text={`已完成 ${statusCounts.completed}`} />
          </li>
        )}
        {statusCounts.failed > 0 && (
          <li>
            <Badge status="error" text={`失败 ${statusCounts.failed}`} />
          </li>
        )}
      </ul>
    );
  };

  const getStatusTag = (status: string) => {
    const statusMap = {
      pending: { color: 'warning', text: '待执行' },
      scheduled: { color: 'processing', text: '已调度' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' }
    };
    const config = statusMap[status as keyof typeof statusMap];
    return <Tag color={config?.color}>{config?.text}</Tag>;
  };

  return (
    <Card
      title={
        <Space>
          <CalendarOutlined />
          <span>调度日历</span>
          <Select
            value={selectedConfig}
            onChange={setSelectedConfig}
            style={{ width: 200 }}
            placeholder="选择发布配置"
          >
            {configs.map(config => (
              <Select.Option key={config.config_id} value={config.config_id}>
                {config.config_name}
              </Select.Option>
            ))}
          </Select>
        </Space>
      }
      extra={
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setGenerateModalVisible(true)}
            disabled={!selectedConfig}
          >
            生成槽位
          </Button>
          <Tooltip title="刷新">
            <Button icon={<ReloadOutlined />} onClick={loadSlots} loading={loading} />
          </Tooltip>
        </Space>
      }
    >
      <Calendar
        value={selectedDate}
        onChange={(date) => {
          setSelectedDate(date);
          setModalVisible(true);
        }}
        dateCellRender={dateCellRender}
      />

      <Modal
        title={`${selectedDate.format('YYYY年MM月DD日')} 调度详情`}
        visible={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <List
          loading={loading}
          dataSource={slots.filter(slot => 
            dayjs(slot.slot_time).format('YYYY-MM-DD') === selectedDate.format('YYYY-MM-DD')
          )}
          renderItem={slot => (
            <List.Item>
              <List.Item.Meta
                avatar={<ClockCircleOutlined />}
                title={
                  <Space>
                    <span>{dayjs(slot.slot_time).format('HH:mm')}</span>
                    {getStatusTag(slot.status)}
                  </Space>
                }
                description={
                  <Space direction="vertical" size={0}>
                    <span>账号: {slot.account_id}</span>
                    {slot.task_id && <span>任务ID: {slot.task_id}</span>}
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Modal>

      <Modal
        title="生成调度槽位"
        visible={generateModalVisible}
        onCancel={() => setGenerateModalVisible(false)}
        onOk={() => {
          const date = dayjs();
          const startTime = dayjs().hour(6).minute(0);
          const endTime = dayjs().hour(23).minute(0);
          handleGenerateSlots({
            date,
            startTime,
            endTime,
            strategy: 'even'
          });
        }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <DatePicker
            style={{ width: '100%' }}
            placeholder="选择日期"
            defaultValue={selectedDate}
          />
          <TimePicker
            style={{ width: '100%' }}
            placeholder="开始时间"
            defaultValue={dayjs().hour(6).minute(0)}
            format="HH:mm"
          />
          <TimePicker
            style={{ width: '100%' }}
            placeholder="结束时间"
            defaultValue={dayjs().hour(23).minute(0)}
            format="HH:mm"
          />
          <Select
            style={{ width: '100%' }}
            placeholder="分配策略"
            defaultValue="even"
          >
            <Select.Option value="even">均匀分布</Select.Option>
            <Select.Option value="random">随机分布</Select.Option>
          </Select>
        </Space>
      </Modal>
    </Card>
  );
};

export default ScheduleCalendar;