import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // 路径别名：@ -> src（ESM 安全写法）
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    host: true,
    open: true,
    // 开发环境代理：将 /api 转发到后端 FastAPI 服务
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // 后端统一前缀为 /api/v1，无需 rewrite
      },
    },
  },
  build: {
    target: 'es2020',
    outDir: 'dist',
    sourcemap: false,
    // 分包策略：将第三方依赖拆分，提升缓存命中率
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          antd: ['antd', '@ant-design/icons'],
          echarts: ['echarts', 'echarts-for-react'],
        },
      },
    },
  },
});
