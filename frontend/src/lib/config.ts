const backendPort = "8000";

function resolveApiBaseUrl() {
  const configuredUrl = import.meta.env.VITE_API_BASE_URL?.trim();

  // VITE_API_BASE_URL 留空或设置为 auto 时，使用当前页面的主机名访问后端。
  // 这样局域网联调时不需要手动修改前端代码。
  if (!configuredUrl || configuredUrl.toLowerCase() === "auto") {
    return `${window.location.protocol}//${window.location.hostname}:${backendPort}`;
  }

  return configuredUrl.replace(/\/$/, "");
}

export const apiBaseUrl = resolveApiBaseUrl();
