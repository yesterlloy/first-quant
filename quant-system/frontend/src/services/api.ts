import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
} from 'axios';
import { message } from 'antd';
import { useUserStore } from '../stores/useUserStore';

/**
 * 后端统一响应结构（对应 backend/app/schemas/common.py::ApiResponse）
 */
export interface ApiResponse<T = unknown> {
  /** 业务状态码，0 表示成功 */
  code: number;
  /** 提示信息 */
  message: string;
  /** 业务数据 */
  data: T | null;
  /** 附加详情（如校验错误字段） */
  details?: unknown;
  /** 服务端时间戳（秒） */
  timestamp: number;
}

/**
 * 用户信息（对应 backend/app/schemas/user.py::UserOut）
 */
export interface UserInfo {
  id: number;
  username: string;
  email: string | null;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * 登录响应（对应 backend/app/schemas/user.py::LoginResponse）
 */
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}

/**
 * 业务错误：拦截器/封装层抛出，携带业务状态码与详情。
 */
export class ApiError extends Error {
  code: number;
  details?: unknown;

  constructor(message: string, code: number, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.details = details;
  }
}

/** 创建 Axios 实例 */
const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: Number(import.meta.env.VITE_REQUEST_TIMEOUT) || 30_000,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * 请求拦截器：自动注入 JWT Token
 */
request.interceptors.request.use(
  (config) => {
    const token = useUserStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

/**
 * 响应拦截器：仅处理 HTTP 层错误（成功响应由 http 封装层拆包）
 * - 401：Token 失效，清理登录态并跳转登录页
 * - 其他：统一弹出错误提示
 */
request.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<ApiResponse>) => {
    const status = error.response?.status;
    const payload = error.response?.data;

    if (status === 401) {
      useUserStore.getState().logout();
      message.error('登录已过期，请重新登录');
      // 避免在登录页重复跳转
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }

    const msg = payload?.message || error.message || '网络异常，请稍后重试';
    message.error(msg);
    return Promise.reject(error);
  },
);

/**
 * 拆包 ApiResponse：code !== 0 抛出 ApiError，否则返回 data 字段。
 */
async function unwrap<T>(p: Promise<AxiosResponse<ApiResponse<T>>>): Promise<T> {
  const { data: res } = await p;
  if (res.code !== 0) {
    throw new ApiError(res.message || '请求失败', res.code, res.details);
  }
  return res.data as T;
}

/**
 * 类型化 HTTP 封装：自动拆包统一响应，返回业务数据。
 * 适用于返回 ApiResponse 包装的接口。
 */
export const http = {
  get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return unwrap<T>(request.get<ApiResponse<T>>(url, config));
  },
  post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return unwrap<T>(request.post<ApiResponse<T>>(url, data, config));
  },
  put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return unwrap<T>(request.put<ApiResponse<T>>(url, data, config));
  },
  delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return unwrap<T>(request.delete<ApiResponse<T>>(url, config));
  },
};

export default request;
