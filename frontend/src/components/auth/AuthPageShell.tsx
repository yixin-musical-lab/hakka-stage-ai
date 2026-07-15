import type { ReactNode } from "react";
import { Link } from "react-router";

export function AuthPageShell({ children }: { children: ReactNode }) {
  return (
    <main className="auth-page">
      <section className="auth-brand-panel" aria-label="平台介绍">
        <Link className="brand-mark auth-brand" to="/">
          <span className="brand-seal">客</span>
          <span>
            <strong>客韵智演</strong>
            <small>AI 歌舞剧教学与排演辅助系统</small>
          </span>
        </Link>
        <div className="auth-brand-copy">
          <p className="eyebrow">教学与排演工作台</p>
          <h1>让每一次备课、排练与复盘都有清楚的入口</h1>
          <p>登录后统一管理教案、课堂互动、剧本创编、训练计划和排练记录。</p>
        </div>
        <p className="auth-boundary-note">平台不开放匿名注册；新账号由已登录成员统一创建和分发。</p>
      </section>
      <section className="auth-form-panel">{children}</section>
    </main>
  );
}
