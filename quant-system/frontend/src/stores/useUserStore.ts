import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserInfo } from '../services/api';

/**
 * 用户状态：Token 与用户信息，使用 persist 中间件持久化到 localStorage，
 * 避免刷新页面后丢失登录态。
 */
interface UserState {
  /** JWT 访问令牌 */
  token: string | null;
  /** 当前用户信息 */
  user: UserInfo | null;
  /** 登录成功后写入 token 与用户信息 */
  setAuth: (token: string, user: UserInfo) => void;
  /** 仅更新用户信息（如编辑个人资料后） */
  setUser: (user: UserInfo) => void;
  /** 退出登录：清空 token 与用户信息 */
  logout: () => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      setUser: (user) => set({ user }),
      logout: () => set({ token: null, user: null }),
    }),
    {
      name: 'quant-auth', // localStorage 存储 key
      // 仅持久化 token 与 user，不持久化方法
      partialize: (state) => ({ token: state.token, user: state.user }),
    },
  ),
);
