const TIME_ZONE_SUFFIX_PATTERN = /(?:Z|[+-]\d{2}:?\d{2})$/i;

/**
 * 后端数据库统一保存 UTC-naive 时间，接口返回值通常不带 Z 或时区偏移。
 * 这里为无时区标记的时间补上 UTC 标记，避免浏览器误把它当作本地时间。
 */
export function parseApiDateTime(value: string) {
  const trimmedValue = value.trim();
  const normalizedValue = TIME_ZONE_SUFFIX_PATTERN.test(trimmedValue) ? trimmedValue : `${trimmedValue}Z`;
  const parsedValue = new Date(normalizedValue);
  return Number.isNaN(parsedValue.getTime()) ? null : parsedValue;
}

/** 返回统一的时间戳，供跨模块列表排序使用；非法时间排到有效记录之后。 */
export function apiDateTimeToEpoch(value: string) {
  return parseApiDateTime(value)?.getTime() ?? 0;
}

/** 为 time 元素输出带 UTC 标记的标准 ISO 字符串，同时兼容历史无时区数据。 */
export function normalizeApiDateTime(value: string) {
  return parseApiDateTime(value)?.toISOString() ?? value;
}

/** 将接口 UTC 时间转换为访问者浏览器所在时区的当地时间。 */
export function formatDateTime(value: string) {
  const parsedValue = parseApiDateTime(value);
  if (!parsedValue) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(parsedValue);
}

/** 仅显示当地时分，用于移动端窄卡片；完整时间仍保留在语义标签中。 */
export function formatTime(value: string) {
  const parsedValue = parseApiDateTime(value);
  if (!parsedValue) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(parsedValue);
}

/** 带年份和秒数的完整当地时间，用于账号等详情信息。 */
export function formatFullDateTime(value: string) {
  const parsedValue = parseApiDateTime(value);
  if (!parsedValue) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(parsedValue);
}
