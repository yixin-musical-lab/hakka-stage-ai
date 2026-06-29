import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// shadcn/ui 与 Tailwind 工具类统一通过 cn 合并，避免条件样式和重复类名互相覆盖。
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
