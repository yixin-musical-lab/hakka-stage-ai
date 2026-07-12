import type { ReactNode } from "react";
import { Link, NavLink } from "react-router";

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <Link className="brand-mark" to="/">
          <span className="brand-seal">客</span>
          <span>
            <strong>客韵智演</strong>
            <small>AI 歌舞剧教学与排演辅助系统</small>
          </span>
        </Link>
        <nav className="main-nav" aria-label="主导航">
          <NavLink to="/" end>
            首页
          </NavLink>
          <NavLink to="/lesson-plans/generate">教案生成</NavLink>
          <NavLink to="/interactions">课堂互动</NavLink>
          <NavLink to="/musical-scripts/generate">剧本创编</NavLink>
          <NavLink to="/song-adaptations">唱段适配</NavLink>
          <NavLink to="/musical-fusion-plans">歌舞融合</NavLink>
          <NavLink to="/role-training-plans">分角色训练</NavLink>
          <NavLink to="/movement-guides">示范材料</NavLink>
          <NavLink to="/practice-submissions">课后练习</NavLink>
          <NavLink to="/health">系统状态</NavLink>
        </nav>
      </header>
      {children}
    </div>
  );
}
