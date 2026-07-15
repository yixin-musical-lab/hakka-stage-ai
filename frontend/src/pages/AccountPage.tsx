import { useEffect, useState, type FormEvent } from "react";
import { UserPlus } from "lucide-react";
import { Link } from "react-router";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { PageTitle } from "../components/ui/PageTitle";
import { useAuth } from "../contexts/AuthContext";

export function AccountPage() {
  const { user, updateProfile, changePassword } = useAuth();
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [profileNotice, setProfileNotice] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirmation, setNewPasswordConfirmation] = useState("");
  const [passwordNotice, setPasswordNotice] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => setDisplayName(user?.display_name ?? ""), [user?.display_name]);
  if (!user) return null;

  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingProfile(true);
    setProfileNotice("");
    try {
      await updateProfile(displayName);
      setProfileNotice("账号资料已保存。");
    } catch (caughtError) {
      setProfileNotice(caughtError instanceof Error ? caughtError.message : "资料保存失败。");
    } finally {
      setSavingProfile(false);
    }
  }

  async function handlePasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (newPassword !== newPasswordConfirmation) {
      setPasswordNotice("两次输入的新密码不一致。");
      return;
    }
    setSavingPassword(true);
    setPasswordNotice("");
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setNewPasswordConfirmation("");
      setPasswordNotice("密码已更新，下次登录请使用新密码。");
    } catch (caughtError) {
      setPasswordNotice(caughtError instanceof Error ? caughtError.message : "密码修改失败。");
    } finally {
      setSavingPassword(false);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="账号管理"
        title="个人账号"
        description="查看账号身份，修改显示名称、更新登录密码，或为平台成员创建账号。"
        action={
          <Button asChild>
            <Link to="/accounts/new"><UserPlus aria-hidden="true" />创建账号</Link>
          </Button>
        }
      />
      <section className="account-layout">
        <Card>
          <CardHeader>
            <CardTitle>账号概览</CardTitle>
            <CardDescription>邮箱和账号身份由创建信息确定，首版暂不支持自行修改。</CardDescription>
          </CardHeader>
          <CardContent className="account-summary">
            <div><span>显示名称</span><strong>{user.display_name}</strong></div>
            <div><span>登录邮箱</span><strong>{user.email}</strong></div>
            <div><span>账号身份</span><Badge variant="secondary">{user.role === "teacher" ? "老师" : "学生"}</Badge></div>
            <div><span>注册时间</span><strong>{new Date(user.created_at).toLocaleString("zh-CN")}</strong></div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>修改资料</CardTitle><CardDescription>显示名称会出现在平台右上角的账号入口。</CardDescription></CardHeader>
          <CardContent>
            <form className="account-form" onSubmit={handleProfileSubmit}>
              <div className="auth-field"><Label htmlFor="account-name">显示名称</Label><Input id="account-name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} minLength={2} maxLength={40} required /></div>
              {profileNotice ? <p className="form-notice" role="status">{profileNotice}</p> : null}
              <Button type="submit" disabled={savingProfile}>{savingProfile ? "正在保存…" : "保存资料"}</Button>
            </form>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>修改密码</CardTitle><CardDescription>更新前需要再次输入当前密码。</CardDescription></CardHeader>
          <CardContent>
            <form className="account-form" onSubmit={handlePasswordSubmit}>
              <div className="auth-field"><Label htmlFor="current-password">当前密码</Label><Input id="current-password" type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></div>
              <div className="auth-field"><Label htmlFor="new-password">新密码</Label><Input id="new-password" type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={8} maxLength={128} required /><small>8-128 位，至少包含一个字母和一个数字。</small></div>
              <div className="auth-field"><Label htmlFor="new-password-confirmation">确认新密码</Label><Input id="new-password-confirmation" type="password" autoComplete="new-password" value={newPasswordConfirmation} onChange={(event) => setNewPasswordConfirmation(event.target.value)} minLength={8} maxLength={128} required /></div>
              {passwordNotice ? <p className="form-notice" role="status">{passwordNotice}</p> : null}
              <Button type="submit" disabled={savingPassword}>{savingPassword ? "正在更新…" : "更新密码"}</Button>
            </form>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
