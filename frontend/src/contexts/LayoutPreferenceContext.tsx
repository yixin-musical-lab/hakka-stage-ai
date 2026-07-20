import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type LayoutMode = "classic" | "workspace";

type LayoutPreferenceContextValue = {
  layoutMode: LayoutMode;
  setLayoutMode: (mode: LayoutMode) => void;
};

// v1 在首次进入页面时会自动写入 workspace，无法区分“系统默认”与“用户主动选择”。
// 使用新键重新建立清晰语义：没有 v2 偏好时始终进入经典布局，只有用户手动切换后才持久化。
const STORAGE_KEY = "hakka-stage-layout-mode-v2";
const LayoutPreferenceContext = createContext<LayoutPreferenceContextValue | null>(null);

function readStoredLayoutMode(): LayoutMode {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "workspace" ? "workspace" : "classic";
  } catch {
    // 浏览器禁用本地存储时仍默认使用经典布局，只是不跨刷新保存用户选择。
    return "classic";
  }
}

export function LayoutPreferenceProvider({ children }: { children: ReactNode }) {
  const [layoutMode, setLayoutModeState] = useState<LayoutMode>(readStoredLayoutMode);

  const setLayoutMode = useCallback((mode: LayoutMode) => {
    setLayoutModeState(mode);
    try {
      // 只在用户通过界面主动切换时写入，首次渲染不再悄悄保存新布局。
      window.localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // 存储失败不影响当前会话内切换。
    }
  }, []);

  useEffect(() => {
    document.documentElement.dataset.layout = layoutMode;
  }, [layoutMode]);

  useEffect(() => {
    // 同一账号打开多个标签页时同步布局偏好，避免页面之间显示不一致。
    const syncLayoutMode = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY && (event.newValue === "classic" || event.newValue === "workspace")) {
        setLayoutModeState(event.newValue);
      }
    };
    window.addEventListener("storage", syncLayoutMode);
    return () => window.removeEventListener("storage", syncLayoutMode);
  }, []);

  const value = useMemo(
    () => ({ layoutMode, setLayoutMode }),
    [layoutMode, setLayoutMode],
  );

  return <LayoutPreferenceContext.Provider value={value}>{children}</LayoutPreferenceContext.Provider>;
}

export function useLayoutPreference() {
  const context = useContext(LayoutPreferenceContext);
  if (!context) throw new Error("useLayoutPreference 必须在 LayoutPreferenceProvider 内使用。");
  return context;
}
