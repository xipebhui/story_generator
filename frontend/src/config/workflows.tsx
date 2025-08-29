/**
 * 工作流配置
 * 定义不同类型的YouTube创作工作流
 */

import React from 'react';
import { 
  BookOutlined, 
  PictureOutlined, 
  PlayCircleOutlined,
  FieldTimeOutlined,
  UserOutlined,
  FolderOutlined,
  YoutubeOutlined
} from '@ant-design/icons';

export interface WorkflowField {
  name: string;
  label: string;
  type: 'text' | 'select' | 'number' | 'switch' | 'folder';
  required?: boolean;
  placeholder?: string;
  defaultValue?: any;
  options?: { label: string; value: any }[];
  min?: number;
  max?: number;
  tooltip?: string;
  icon?: React.ReactNode;
}

export interface WorkflowConfig {
  key: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  gradient: string;
  fields: WorkflowField[];
  tags: string[];
}

export const workflows: WorkflowConfig[] = [
  {
    key: 'youtube-story',
    name: 'YouTube故事',
    description: '将YouTube视频转化为引人入胜的故事内容，配以专业语音和精美画面',
    icon: <BookOutlined />,
    color: '#722ED1',
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    fields: [
      {
        name: 'video_id',
        label: 'YouTube视频ID',
        type: 'text',
        required: true,
        placeholder: '请输入11位YouTube视频ID',
        tooltip: '例如：dQw4w9WgXcQ',
        icon: <YoutubeOutlined />
      },
      {
        name: 'creator_id',
        label: '创作者ID',
        type: 'text',
        required: true,
        placeholder: '请输入创作者标识',
        tooltip: '用于区分不同创作者的作品',
        icon: <UserOutlined />
      },
      {
        name: 'account_name',
        label: '发布账号',
        type: 'select',
        required: false,
        placeholder: '选择发布账号（可选）',
        tooltip: '选择要发布到的YouTube账号',
        icon: <UserOutlined />,
        options: []  // 将在组件中动态加载
      },
      {
        name: 'gender',
        label: '语音性别',
        type: 'select',
        required: true,
        defaultValue: 1,
        options: [
          { label: '女声', value: 1 },
          { label: '男声', value: 0 }
        ]
      },
      {
        name: 'duration',
        label: '视频时长(秒)',
        type: 'number',
        required: true,
        defaultValue: 60,
        min: 30,
        max: 300,
        icon: <FieldTimeOutlined />
      },
      {
        name: 'image_dir',
        label: '图片库目录',
        type: 'folder',
        placeholder: '选择图片素材目录(可选)',
        icon: <FolderOutlined />
      },
      {
        name: 'export_video',
        label: '自动导出视频',
        type: 'switch',
        defaultValue: true,
        tooltip: '是否在草稿生成后自动导出视频文件'
      },
      {
        name: 'enable_subtitle',
        label: '启用字幕',
        type: 'switch',
        defaultValue: true,
        tooltip: '是否在视频中添加字幕'
      }
    ],
    tags: ['故事创作', '语音合成', '视频生成']
  },
  {
    key: 'youtube-comic',
    name: 'YouTube漫画',
    description: '将YouTube内容转化为漫画风格的视频，打造独特的视觉体验',
    icon: <PictureOutlined />,
    color: '#F5222D',
    gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    fields: [
      {
        name: 'video_id',
        label: 'YouTube视频ID',
        type: 'text',
        required: true,
        placeholder: '请输入11位YouTube视频ID',
        tooltip: '例如：dQw4w9WgXcQ',
        icon: <YoutubeOutlined />
      },
      {
        name: 'creator_id',
        label: '创作者ID',
        type: 'text',
        required: true,
        placeholder: '请输入创作者标识',
        icon: <UserOutlined />
      },
      {
        name: 'comic_style',
        label: '漫画风格',
        type: 'select',
        required: true,
        defaultValue: 'manga',
        options: [
          { label: '日式漫画', value: 'manga' },
          { label: '美式漫画', value: 'american' },
          { label: '欧式漫画', value: 'european' },
          { label: '韩式条漫', value: 'webtoon' }
        ]
      },
      {
        name: 'panel_layout',
        label: '分镜布局',
        type: 'select',
        required: true,
        defaultValue: 'dynamic',
        options: [
          { label: '动态分镜', value: 'dynamic' },
          { label: '传统四格', value: 'four-panel' },
          { label: '长条漫画', value: 'scroll' },
          { label: '电影分镜', value: 'cinematic' }
        ]
      },
      {
        name: 'duration',
        label: '视频时长(秒)',
        type: 'number',
        required: true,
        defaultValue: 90,
        min: 60,
        max: 300,
        icon: <FieldTimeOutlined />
      },
      {
        name: 'color_scheme',
        label: '配色方案',
        type: 'select',
        defaultValue: 'vibrant',
        options: [
          { label: '鲜艳多彩', value: 'vibrant' },
          { label: '黑白经典', value: 'monochrome' },
          { label: '复古怀旧', value: 'retro' },
          { label: '柔和粉彩', value: 'pastel' }
        ]
      },
      {
        name: 'add_effects',
        label: '添加特效',
        type: 'switch',
        defaultValue: true,
        tooltip: '添加漫画特效如速度线、气泡音效等'
      }
    ],
    tags: ['漫画创作', '视觉艺术', '创意视频']
  },
  {
    key: 'video-merge',
    name: '视频拼接',
    description: '将竖屏和横屏视频智能拼接，创建专业的剪映草稿',
    icon: <PlayCircleOutlined />,
    color: '#52C41A',
    gradient: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
    fields: [
      {
        name: 'portrait_folder',
        label: '竖屏视频文件夹',
        type: 'folder',
        required: true,
        placeholder: '选择包含竖屏视频的文件夹',
        tooltip: '包含9:16竖屏视频的文件夹路径',
        icon: <FolderOutlined />
      },
      {
        name: 'landscape_folder',
        label: '横屏视频文件夹',
        type: 'folder',
        required: true,
        placeholder: '选择包含横屏视频的文件夹',
        tooltip: '包含16:9横屏视频的文件夹路径',
        icon: <FolderOutlined />
      },
      {
        name: 'custom_id',
        label: '自定义ID',
        type: 'text',
        required: false,
        placeholder: '输入自定义任务ID（可选）',
        tooltip: '用于标识任务的自定义ID',
        icon: <UserOutlined />
      }
    ],
    tags: ['视频拼接', '剪映草稿', '创意混剪']
  }
];

// 根据key获取工作流配置
export const getWorkflowConfig = (key: string): WorkflowConfig | undefined => {
  return workflows.find(w => w.key === key);
};

// 获取工作流的默认值
export const getWorkflowDefaults = (key: string): Record<string, any> => {
  const workflow = getWorkflowConfig(key);
  if (!workflow) return {};
  
  const defaults: Record<string, any> = {};
  workflow.fields.forEach(field => {
    if (field.defaultValue !== undefined) {
      defaults[field.name] = field.defaultValue;
    }
  });
  return defaults;
};