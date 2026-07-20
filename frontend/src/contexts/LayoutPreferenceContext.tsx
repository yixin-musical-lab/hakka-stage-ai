import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type LayoutMode = "classic" | "workspace";

type LayoutPreferenceContextValue = {
  layoutMode: LayoutMode;
  setLayoutMode: (mode: LayoutMode) => void;
};

const STORAGE_KEY = "hakka-stage-layout-mode";
const LayoutPreferenceContext = createContext<LayoutPreferenceContextValue | null>(null);

function readStoredLayoutMode(): LayoutMode {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "classic" ? "classic" : "workspace";
  } catch {
    // 浏览器禁用本地存储时仍可使用新工作台布局，只是不跨刷新保存偏好。
    return "workspace";
  }
}

export function LayoutPreferenceProvider({ children }: { children: ReactNode }) {
  const [layoutMode, setLayoutModeState] = useState<LayoutMode>(readStoredLayoutMode);

  useEffect(() => {
    document.documentElement.dataset.layout = layoutMode;
    try {
      window.localStorage.setItem(STORAGE_KEY, layoutMode);
    } catch {
      // 存储失败不影响当前会话内切换。
    }
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
    () => ({ layoutMode, setLayoutMode: setLayoutModeState }),
    [layoutMode],
  );

  return <LayoutPreferenceContext.Provider value={value}>{children}</LayoutPreferenceContext.Provider>;
}

export function useLayoutPreference() {
  const context = useContext(LayoutPreferenceContext);
  if (!context) throw new Error("useLayoutPreference 必须在 LayoutPreferenceProvider 内使用。");
  return context;
}
