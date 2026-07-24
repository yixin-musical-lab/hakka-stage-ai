import {
  Activity,
  BookOpen,
  ChevronDown,
  Clapperboard,
  Drama,
  Film,
  FolderKanban,
  GraduationCap,
  Home,
  Library,
  LogOut,
  Menu,
  MessageSquareText,
  Music2,
  PanelsTopLeft,
  Plus,
  Search,
  Sparkles,
  UserRound,
  Users,
  Video,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ComponentType, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router";
import { useAuth } from "../../contexts/AuthContext";
import { useLayoutPreference, type LayoutMode } from "../../contexts/LayoutPreferenceContext";
import { Button } from "../ui/button";

type NavigationItem = {
  label: string;
  description: string;
  to: string;
  icon: ComponentType<{ "aria-hidden"?: boolean; className?: string }>;
};

type NavigationGroup = {
  label: string;
  items: NavigationItem[];
};

// 工作台布局按老师的业务闭环分组；经典布局继续保留原有顶部平铺导航。
const navigationGroups: NavigationGroup[] = [
  {
    label: "工作总览",
    items: [
      { label: "项目工作台", description: "查看阶段、资产与最近工作", to: "/", icon: Home },
        { label: "媒体创作工作台", description: "克隆音频与图生图", to: "/media-studio", icon: Sparkles },
    ],
  },
  {
    label: "教学闭环",
    items: [
      { label: "教案", description: "生成、编辑与管理教案", to: "/lesson-plans", icon: BookOpen },
      { label: "课堂互动", description: "课堂执行方案与互动脚本", to: "/interactions", icon: MessageSquareText },
      { label: "课后练习", description: "练习提交、观察与反馈", to: "/practice-submissions", icon: GraduationCap },
    ],
  },
  {
    label: "创编与排演",
    items: [
      { label: "剧本创编", description: "人物、分幕剧情与台词", to: "/musical-scripts", icon: Drama },
      { label: "唱段适配", description: "歌词、唱段与音乐结构", to: "/song-adaptations", icon: Music2 },
      { label: "歌舞融合", description: "唱、跳、队形与衔接", to: "/musical-fusion-plans", icon: Sparkles },
      { label: "分角色训练", description: "角色任务与排练目标", to: "/role-training-plans", icon: Users },
      { label: "示范材料", description: "动作图解与示范素材", to: "/movement-guides", icon: Video },
      { label: "排练复盘", description: "排练问题、改进计划与反思", to: "/rehearsal-reviews", icon: Clapperboard },
      { label: "媒体工作台", description: "音频、图像、视频与动作模仿", to: "/media-studio", icon: Film },
    ],
  },
];

const createItems = [
  { label: "新建教案", to: "/lesson-plans/generate", icon: BookOpen },
  { label: "新建课堂互动", to: "/interactions/generate", icon: MessageSquareText },
  { label: "新建剧本", to: "/musical-scripts/generate", icon: Drama },
  { label: "新建排练复盘", to: "/rehearsal-reviews/generate", icon: Clapperboard },
  { label: "生成 Wan 视频", to: "/media-studio/veo", icon: Film },
  { label: "创建动作模仿", to: "/media-studio/motion-transfer", icon: Clapperboard },
];

const classicNavigationItems = [
  { label: "首页", to: "/", end: true },
    { label: "媒体工作台", to: "/media-studio" },
  { label: "教案生成", to: "/lesson-plans/generate" },
  { label: "课堂互动", to: "/interactions" },
  { label: "剧本创编", to: "/musical-scripts/generate" },
  { label: "唱段适配", to: "/song-adaptations" },
  { label: "歌舞融合", to: "/musical-fusion-plans" },
  { label: "分角色训练", to: "/role-training-plans" },
  { label: "排练复盘", to: "/rehearsal-reviews" },
  { label: "示范材料", to: "/movement-guides" },
  { label: "课后练习", to: "/practice-submissions" },
  { label: "系统状态", to: "/health" },
];

function getPageContext(pathname: string) {
  if (pathname === "/") return { eyebrow: "工作空间", title: "项目工作台" };
  if (pathname.startsWith("/media-studio")) return { eyebrow: "AI 媒体", title: "媒体创作工作台" };
  if (pathname.startsWith("/lesson-plans")) return { eyebrow: "教学闭环", title: "教案" };
  if (pathname.startsWith("/interactions")) return { eyebrow: "教学闭环", title: "课堂互动" };
  if (pathname.startsWith("/practice-submissions")) return { eyebrow: "教学闭环", title: "课后练习" };
  if (pathname.startsWith("/musical-scripts")) return { eyebrow: "创编排演", title: "剧本创编" };
  if (pathname.startsWith("/song-adaptations")) return { eyebrow: "创编排演", title: "唱段适配" };
  if (pathname.startsWith("/musical-fusion-plans")) return { eyebrow: "创编排演", title: "歌舞融合" };
  if (pathname.startsWith("/role-training-plans")) return { eyebrow: "创编排演", title: "分角色训练" };
  if (pathname.startsWith("/movement-guides")) return { eyebrow: "创编排演", title: "示范材料" };
  if (pathname.startsWith("/rehearsal-reviews")) return { eyebrow: "创编排演", title: "排练复盘" };
  if (pathname.startsWith("/media-studio")) return { eyebrow: "媒体创作", title: "媒体创作工作台" };
  if (pathname.startsWith("/account")) return { eyebrow: "账号", title: "个人中心" };
  if (pathname.startsWith("/health")) return { eyebrow: "系统", title: "服务状态" };
  return { eyebrow: "工作空间", title: "客韵智演" };
}

function LayoutModeSwitch({ placement }: { placement: "classic" | "sidebar" }) {
  const { layoutMode, setLayoutMode } = useLayoutPreference();

  return (
    <label className={`layout-mode-switch layout-mode-switch--${placement}`}>
      <PanelsTopLeft aria-hidden />
      <span>界面布局</span>
      <select
        aria-label="选择界面布局"
        value={layoutMode}
        onChange={(event) => setLayoutMode(event.target.value as LayoutMode)}
      >
        <option value="workspace">工作台布局</option>
        <option value="classic">经典布局</option>
      </select>
    </label>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { layoutMode } = useLayoutPreference();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const createMenuRef = useRef<HTMLDetailsElement>(null);
  const pageContext = getPageContext(location.pathname);
  const workspaceMode = layoutMode === "workspace";

  const searchableItems = useMemo(() => navigationGroups.flatMap((group) => group.items), []);
  const searchResults = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLocaleLowerCase();
    if (!normalizedQuery) return [];
    return searchableItems
      .filter((item) => `${item.label}${item.description}`.toLocaleLowerCase().includes(normalizedQuery))
      .slice(0, 6);
  }, [searchQuery, searchableItems]);

  useEffect(() => {
    // 路由或布局切换后收起抽屉，避免经典布局仍残留页面滚动锁。
    setSidebarOpen(false);
    setSearchQuery("");
    if (createMenuRef.current) createMenuRef.current.open = false;
  }, [location.pathname, layoutMode]);

  useEffect(() => {
    if (!sidebarOpen || !workspaceMode) return;

    const previousOverflow = document.body.style.overflow;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSidebarOpen(false);
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [sidebarOpen, workspaceMode]);

  useEffect(() => {
    const desktopMedia = window.matchMedia("(min-width: 1241px)");
    const closeDrawerOnDesktop = (event: MediaQueryListEvent) => {
      if (event.matches) setSidebarOpen(false);
    };
    desktopMedia.addEventListener("change", closeDrawerOnDesktop);
    return () => desktopMedia.removeEventListener("change", closeDrawerOnDesktop);
  }, []);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (searchResults[0]) navigate(searchResults[0].to);
  }

  return (
    <div className={`${workspaceMode ? "app-shell app-shell--workspace" : "app-shell app-shell--classic"}${sidebarOpen ? " sidebar-open" : ""}`}>
      {workspaceMode ? (
        <aside className="app-sidebar" aria-label="全站导航">
          <Link className="brand-mark" to="/" aria-label="客韵智演项目工作台">
            <span className="brand-seal">客</span>
            <span className="brand-copy"><strong>客韵智演</strong><small>教学与排演工作空间</small></span>
          </Link>

          <LayoutModeSwitch placement="sidebar" />

          <details className="sidebar-create" ref={createMenuRef}>
            <summary>
              <span><Plus aria-hidden />新建内容</span>
              <ChevronDown aria-hidden className="sidebar-create-chevron" />
            </summary>
            <div className="sidebar-create-menu">
              {createItems.map((item) => {
                const Icon = item.icon;
                return <Link key={item.to} to={item.to}><Icon aria-hidden /><span>{item.label}</span></Link>;
              })}
            </div>
          </details>

          <nav className="sidebar-nav" aria-label="业务导航">
            {navigationGroups.map((group) => (
              <section className="sidebar-nav-group" key={group.label} aria-labelledby={`nav-${group.label}`}>
                <h2 id={`nav-${group.label}`}>{group.label}</h2>
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink key={item.to} to={item.to} end={item.to === "/"}>
                      <Icon aria-hidden />
                      <span><strong>{item.label}</strong><small>{item.description}</small></span>
                    </NavLink>
                  );
                })}
              </section>
            ))}
          </nav>

          <footer className="sidebar-footer">
            <Link to="/account">
              <UserRound aria-hidden />
              <span><strong>{user?.display_name ?? "个人中心"}</strong><small>{user?.role === "student" ? "学生账号" : "老师账号"}</small></span>
            </Link>
            <div className="sidebar-footer-actions">
              <Link to="/health"><Activity aria-hidden /><span>系统状态</span></Link>
              <button type="button" onClick={() => void logout()}><LogOut aria-hidden /><span>退出</span></button>
            </div>
          </footer>
        </aside>
      ) : (
        <header className="app-header">
          <Link className="brand-mark" to="/">
            <span className="brand-seal">客</span>
            <span><strong>客韵智演</strong><small>AI 歌舞剧教学与排演辅助系统</small></span>
          </Link>
          <nav className="main-nav" aria-label="主导航">
            {classicNavigationItems.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end}>{item.label}</NavLink>
            ))}
          </nav>
          <div className="account-nav">
            <LayoutModeSwitch placement="classic" />
            <NavLink className="account-link" to="/account">
              <UserRound aria-hidden />
              <span><strong>{user?.display_name}</strong><small>{user?.role === "student" ? "学生账号" : "老师账号"}</small></span>
            </NavLink>
            <Button type="button" variant="ghost" size="sm" onClick={() => void logout()} title="退出登录">
              <LogOut aria-hidden />退出
            </Button>
          </div>
        </header>
      )}

      <div className={workspaceMode ? "app-workspace" : "classic-workspace"}>
        {workspaceMode ? (
          <header className="workspace-header">
            <button
              className="sidebar-toggle"
              type="button"
              aria-label={sidebarOpen ? "关闭导航" : "打开导航"}
              aria-expanded={sidebarOpen}
              onClick={() => setSidebarOpen((current) => !current)}
            >
              {sidebarOpen ? <X aria-hidden /> : <Menu aria-hidden />}
            </button>

            <Link className="workspace-context" to="/">
              <FolderKanban aria-hidden />
              <span><small>{pageContext.eyebrow}</small><strong>{pageContext.title}</strong></span>
            </Link>

            <form className="workspace-search" role="search" onSubmit={submitSearch}>
              <Search aria-hidden />
              <label className="sr-only" htmlFor="workspace-search-input">搜索功能与页面</label>
              <input
                id="workspace-search-input"
                type="search"
                value={searchQuery}
                placeholder="搜索功能与页面"
                autoComplete="off"
                onChange={(event) => setSearchQuery(event.target.value)}
              />
              <kbd>Enter</kbd>
              {searchQuery ? (
                <div className="workspace-search-results" aria-label="搜索结果">
                  {searchResults.length ? searchResults.map((item) => {
                    const Icon = item.icon;
                    return <Link key={item.to} to={item.to}><Icon aria-hidden /><span><strong>{item.label}</strong><small>{item.description}</small></span></Link>;
                  }) : <p>没有匹配的功能</p>}
                </div>
              ) : null}
            </form>

            <div className="workspace-header-actions">
              <Link className="header-status" to="/health"><span aria-hidden />状态中心</Link>
              <Link className="header-library" to="/lesson-plans"><Library aria-hidden />教案库</Link>
            </div>
          </header>
        ) : null}

        <div key="route-content" className={workspaceMode ? "workspace-content" : "classic-content"}>{children}</div>
      </div>

      {workspaceMode ? (
        <>
          <button
            className="sidebar-scrim"
            type="button"
            aria-label="关闭导航"
            aria-hidden={!sidebarOpen}
            tabIndex={sidebarOpen ? 0 : -1}
            onClick={() => setSidebarOpen(false)}
          />
          <nav className="mobile-bottom-nav" aria-label="移动端快捷导航">
            <NavLink to="/" end><Home aria-hidden /><span>工作台</span></NavLink>
            <NavLink to="/lesson-plans"><BookOpen aria-hidden /><span>教学</span></NavLink>
            <NavLink className="mobile-create" to="/lesson-plans/generate"><Plus aria-hidden /><span>新建</span></NavLink>
            <NavLink to="/musical-scripts"><Drama aria-hidden /><span>创编</span></NavLink>
            <button type="button" onClick={() => setSidebarOpen(true)}><Menu aria-hidden /><span>更多</span></button>
          </nav>
        </>
      ) : null}
    </div>
  );
}
