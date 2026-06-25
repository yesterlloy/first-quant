import request, { type LoginResponse, type UserInfo, http } from './api';

/**
 * 认证服务：封装登录、注册、获取当前用户等接口。
 * 对应后端 backend/app/api/v1/auth.py
 */

export interface RegisterPayload {
  username: string;
  password: string;
  email?: string | null;
  full_name?: string | null;
}

export interface UpdateUserPayload {
  email?: string | null;
  full_name?: string | null;
  password?: string;
}

/**
 * 登录（OAuth2 表单形式提交 username/password）
 * 后端接口：POST /auth/login，返回 LoginResponse（非 ApiResponse 包装）
 */
export async function login(username: string, password: string): Promise<LoginResponse> {
  // OAuth2PasswordRequestForm 要求表单编码
  const form = new URLSearchParams();
  form.append('username', username);
  form.append('password', password);

  const { data } = await request.post<LoginResponse>('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data;
}

/**
 * 注册新用户
 * 后端接口：POST /auth/register
 */
export function register(payload: RegisterPayload): Promise<UserInfo> {
  return http.post<UserInfo>('/auth/register', payload);
}

/**
 * 获取当前登录用户
 * 后端接口：GET /auth/me
 */
export function getCurrentUser(): Promise<UserInfo> {
  return http.get<UserInfo>('/auth/me');
}

/**
 * 更新当前用户信息
 * 后端接口：PUT /auth/me
 */
export function updateCurrentUser(payload: UpdateUserPayload): Promise<UserInfo> {
  return http.put<UserInfo>('/auth/me', payload);
}
