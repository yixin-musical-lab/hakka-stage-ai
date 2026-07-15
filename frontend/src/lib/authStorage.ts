const ACCESS_TOKEN_KEY = "hakka-stage-ai.access-token";

export const AUTH_SESSION_EXPIRED_EVENT = "hakka-stage-ai:session-expired";

export function getAccessToken() {
  // 集中读取访问令牌，避免业务组件直接操作 localStorage。

  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function storeAccessToken(accessToken: string) {
  // 登录成功后保存访问令牌，用于刷新页面后恢复会话。

  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
}

export function clearAccessToken() {
  // 退出登录或令牌失效时清理本地会话。

  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
}

export async function authenticatedFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  /* 为现有业务请求统一补充 Bearer 令牌和 Cookie 凭据。
     后端返回 401 时立即广播会话失效事件，AuthProvider 会把页面带回登录入口。
     这样新增 API 继续复用该方法即可，不需要在每个页面重复处理鉴权。 */

  const headers = new Headers(init.headers);
  const accessToken = getAccessToken();
  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await window.fetch(input, { ...init, headers, credentials: "include" });
  if (response.status === 401 && accessToken) {
    clearAccessToken();
    window.dispatchEvent(new Event(AUTH_SESSION_EXPIRED_EVENT));
  }
  return response;
}
