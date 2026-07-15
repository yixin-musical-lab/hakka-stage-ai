import type {
  AccountCreateForm,
  AuthSession,
  BatchAccountCreateResponse,
  LoginForm,
  UserAccount,
} from "../types";
import { apiBaseUrl } from "./config";
import { authenticatedFetch } from "./authStorage";

async function readAuthError(response: Response) {
  // 兼容后端业务错误和 Pydantic 字段校验错误。

  try {
    const data = (await response.json()) as {
      detail?: string | Array<{ msg?: string }>;
      message?: string;
    };
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((item) => item.msg).filter(Boolean).join("；") || "提交内容校验失败。";
    }
    return data.message ?? `请求失败：${response.status}`;
  } catch {
    return `请求失败：${response.status}`;
  }
}

export async function loginAccount(form: LoginForm) {
  // 登录接口保持公开，但不再提供任何匿名账号创建入口。
  const response = await window.fetch(`${apiBaseUrl}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(form),
  });
  if (!response.ok) throw new Error(await readAuthError(response));
  return (await response.json()) as AuthSession;
}

export async function createAccount(form: AccountCreateForm) {
  const response = await authenticatedFetch(`${apiBaseUrl}/api/accounts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  if (!response.ok) throw new Error(await readAuthError(response));
  return (await response.json()) as UserAccount;
}

export async function createAccountsBatch(accounts: AccountCreateForm[]) {
  const response = await authenticatedFetch(`${apiBaseUrl}/api/accounts/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accounts }),
  });
  if (!response.ok) throw new Error(await readAuthError(response));
  return (await response.json()) as BatchAccountCreateResponse;
}

export async function fetchCurrentAccount(signal?: AbortSignal) {
  const response = await authenticatedFetch(`${apiBaseUrl}/api/account/me`, { signal });
  if (!response.ok) throw new Error(await readAuthError(response));
  return (await response.json()) as UserAccount;
}

export async function updateAccountProfile(displayName: string) {
  const response = await authenticatedFetch(`${apiBaseUrl}/api/account/profile`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: displayName }),
  });
  if (!response.ok) throw new Error(await readAuthError(response));
  return (await response.json()) as UserAccount;
}

export async function updateAccountPassword(currentPassword: string, newPassword: string) {
  const response = await authenticatedFetch(`${apiBaseUrl}/api/account/password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  if (!response.ok) throw new Error(await readAuthError(response));
}

export async function logoutAccount() {
  const response = await authenticatedFetch(`${apiBaseUrl}/api/auth/logout`, { method: "POST" });
  if (!response.ok && response.status !== 401) throw new Error(await readAuthError(response));
}
