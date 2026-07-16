const TIME_ZONE_SUFFIX_PATTERN = /(?:Z|[+-]\d{2}:?\d{2})$/i;

/**
 * 后端数据库统一保存 UTC-naive 时间，接口返回值通常不带 Z 或时区偏移。
 * 这里为无时区标记的时间补上 UTC 标记，避免浏览器误把它当作本地时间。
 */
function parseApiDateTime(value: string) {
  const normalizedValue = TIME_ZONE_SUFFIX_PATTERN.test(value) ? value : `${value}Z`;
  return new Date(normalizedValue);
}

/** 将接口 UTC 时间转换为访问者浏览器所在时区的当地时间。 */
export function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(parseApiDateTime(value));
}

/** 带年份和秒数的完整当地时间，用于账号等详情信息。 */
export function formatFullDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(parseApiDateTime(value));
}
