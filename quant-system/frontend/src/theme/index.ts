import type { ThemeConfig } from 'antd';
import { theme } from 'antd';

/**
 * Ant Design 6 主题配置
 * 量化系统配色：以科技蓝为主色，深色侧边栏 + 浅色内容区
 */
export const themeConfig: ThemeConfig = {
  // 使用默认（亮色）算法；如需暗色可切换 theme.darkAlgorithm
  algorithm: theme.defaultAlgorithm,
  token: {
    // 主色：科技蓝
    colorPrimary: '#1677ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#1677ff',
    // 圆角与字号
    borderRadius: 8,
    fontSize: 14,
    // 链接色
    colorLink: '#1677ff',
    // 布局背景
    colorBgLayout: '#f5f7fa',
  },
  components: {
    Layout: {
      headerBg: '#ffffff',
      headerHeight: 60,
      siderBg: '#001529',
      bodyBg: '#f5f7fa',
    },
    Menu: {
      darkItemBg: '#001529',
      darkSubMenuItemBg: '#000c17',
      darkItemSelectedBg: '#1677ff',
    },
    Card: {
      borderRadiusLG: 10,
    },
    Table: {
      headerBg: '#fafafa',
      headerColor: '#1f1f1f',
      rowHoverBg: '#f5faff',
    },
  },
};
