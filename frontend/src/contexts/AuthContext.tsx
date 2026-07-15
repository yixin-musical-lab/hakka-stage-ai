import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { LoginForm, UserAccount } from "../types";
import {
  fetchCurrentAccount,
  loginAccount,
  logoutAccount,
  updateAccountPassword,
  updateAccountProfile,
} from "../lib/authApi";
import {
  AUTH_SESSION_EXPIRED_EVENT,
  clearAccessToken,
  getAccessToken,
  storeAccessToken,
} from "../lib/authStorage";

type AuthContextValue = {
  user: UserAccount | null;
  checkingSession: boolean;
  login: (form: LoginForm) => Promise<void>;
  logout: () => Promise<void>;
  updateProfile: (displayName: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserAccount | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    // 刷新页面时通过服务端重新确认账号，避免信任本地缓存的用户资料。

    const controller = new AbortController();
    if (!getAccessToken()) {
      setCheckingSession(false);
      return () => controller.abort();
    }

    void fetchCurrentAccount(controller.signal)
      .then(setUser)
      .catch(() => {
        // React StrictMode 会在开发环境主动中止首轮 effect；中止不代表令牌无效。
        if (controller.signal.aborted) return;
        clearAccessToken();
        setUser(null);
      })
      .finally(() => {
        if (!controller.signal.aborted) setCheckingSession(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const handleSessionExpired = () => setUser(null);
    window.addEventListener(AUTH_SESSION_EXPIRED_EVENT, handleSessionExpired);
    return () => window.removeEventListener(AUTH_SESSION_EXPIRED_EVENT, handleSessionExpired);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      checkingSession,
      async login(form) {
        const session = await loginAccount(form);
        storeAccessToken(session.access_token);
        setUser(session.user);
      },
      async logout() {
        try {
          await logoutAccount();
        } finally {
          clearAccessToken();
          setUser(null);
        }
      },
      async updateProfile(displayName) {
        setUser(await updateAccountProfile(displayName));
      },
      async changePassword(currentPassword, newPassword) {
        await updateAccountPassword(currentPassword, newPassword);
      },
    }),
    [checkingSession, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth 必须在 AuthProvider 内使用");
  return context;
}
