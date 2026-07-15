import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { PageTitle } from "../components/ui/PageTitle";
import { Textarea } from "../components/ui/textarea";
import { createAccount, createAccountsBatch } from "../lib/authApi";
import type { AccountCreateForm, AccountRole, UserAccount } from "../types";

const batchJsonTemplate = JSON.stringify(
  {
    accounts: [
      {
        email: "student01@example.com",
        password: "student2026",
        display_name: "学生一",
        role: "student",
      },
      {
        email: "teacher02@example.com",
        password: "teacher2026",
        display_name: "李老师",
        role: "teacher",
      },
    ],
  },
  null,
  2,
);

function parseBatchAccounts(value: string): AccountCreateForm[] {
  // 允许粘贴 { accounts: [...] } 或直接粘贴数组，提交时统一包装成后端结构。

  const parsed = JSON.parse(value) as unknown;
  const accounts = Array.isArray(parsed)
    ? parsed
    : parsed && typeof parsed === "object" && "accounts" in parsed
      ? (parsed as { accounts: unknown }).accounts
      : null;
  if (!Array.isArray(accounts)) throw new Error("JSON 必须是账号数组，或包含 accounts 数组的对象。");
  return accounts as AccountCreateForm[];
}

export function AccountCreatePage() {
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<AccountRole>("student");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [singleNotice, setSingleNotice] = useState("");
  const [batchJson, setBatchJson] = useState(batchJsonTemplate);
  const [batchNotice, setBatchNotice] = useState("");
  const [createdUsers, setCreatedUsers] = useState<UserAccount[]>([]);
  const [creatingSingle, setCreatingSingle] = useState(false);
  const [creatingBatch, setCreatingBatch] = useState(false);

  async function handleSingleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (password !== passwordConfirmation) {
      setSingleNotice("两次输入的密码不一致。");
      return;
    }
    setCreatingSingle(true);
    setSingleNotice("");
    try {
      const user = await createAccount({ display_name: displayName, email, role, password });
      setCreatedUsers([user]);
      setDisplayName("");
      setEmail("");
      setPassword("");
      setPasswordConfirmation("");
      setSingleNotice(`账号 ${user.email} 已创建。`);
    } catch (caughtError) {
      setSingleNotice(caughtError instanceof Error ? caughtError.message : "账号创建失败。");
    } finally {
      setCreatingSingle(false);
    }
  }

  async function handleBatchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreatingBatch(true);
    setBatchNotice("");
    try {
      const accounts = parseBatchAccounts(batchJson);
      const result = await createAccountsBatch(accounts);
      setCreatedUsers(result.users);
      setBatchNotice(`已完整创建 ${result.created_count} 个账号。`);
    } catch (caughtError) {
      setBatchNotice(caughtError instanceof Error ? caughtError.message : "批量创建失败。");
    } finally {
      setCreatingBatch(false);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="账号管理 / 创建账号"
        title="创建平台账号"
        description="仅已登录用户可以创建新账号。支持单个填写，也支持用 JSON 一次创建最多 50 个账号。"
        action={<Button asChild variant="outline"><Link to="/account">返回个人账号</Link></Button>}
      />

      <section className="account-create-layout">
        <Card>
          <CardHeader>
            <CardTitle>单个创建</CardTitle>
            <CardDescription>填写成员资料和初始密码；创建后不会切换当前登录账号。</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="account-form" onSubmit={handleSingleSubmit}>
              <div className="auth-field"><Label htmlFor="create-name">显示名称</Label><Input id="create-name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} minLength={2} maxLength={40} required /></div>
              <div className="auth-field"><Label htmlFor="create-email">登录邮箱</Label><Input id="create-email" type="email" autoComplete="off" value={email} onChange={(event) => setEmail(event.target.value)} required /></div>
              <div className="auth-field">
                <Label htmlFor="create-role">账号身份</Label>
                <select id="create-role" className="auth-select" value={role} onChange={(event) => setRole(event.target.value as AccountRole)}>
                  <option value="teacher">老师</option>
                  <option value="student">学生</option>
                </select>
              </div>
              <div className="auth-field"><Label htmlFor="create-password">初始密码</Label><Input id="create-password" type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} maxLength={128} required /><small>8-128 位，至少包含一个字母和一个数字。</small></div>
              <div className="auth-field"><Label htmlFor="create-password-confirmation">确认初始密码</Label><Input id="create-password-confirmation" type="password" autoComplete="new-password" value={passwordConfirmation} onChange={(event) => setPasswordConfirmation(event.target.value)} minLength={8} maxLength={128} required /></div>
              {singleNotice ? <p className="form-notice" role="status">{singleNotice}</p> : null}
              <Button type="submit" disabled={creatingSingle}>{creatingSingle ? "正在创建…" : "创建账号"}</Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>JSON 批量创建</CardTitle>
            <CardDescription>支持对象或数组格式。任一账号不合法或邮箱已存在时，整批都不会创建。</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="account-form" onSubmit={handleBatchSubmit}>
              <div className="auth-field">
                <Label htmlFor="batch-accounts">账号 JSON</Label>
                <Textarea id="batch-accounts" className="batch-json-input" spellCheck={false} value={batchJson} onChange={(event) => setBatchJson(event.target.value)} required />
                <small>字段：email、password、display_name、role；role 只允许 teacher 或 student。</small>
              </div>
              {batchNotice ? <p className="form-notice" role="status">{batchNotice}</p> : null}
              <Button type="submit" disabled={creatingBatch}>{creatingBatch ? "正在批量创建…" : "校验并批量创建"}</Button>
            </form>
          </CardContent>
        </Card>
      </section>

      {createdUsers.length ? (
        <Card className="created-account-card">
          <CardHeader><CardTitle>本次创建结果</CardTitle><CardDescription>响应不会返回密码，请通过团队约定的安全方式把初始密码交给对应成员。</CardDescription></CardHeader>
          <CardContent>
            <ul className="created-account-list">
              {createdUsers.map((user) => <li key={user.id}><strong>{user.display_name}</strong><span>{user.email}</span><small>{user.role === "teacher" ? "老师" : "学生"}</small></li>)}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </main>
  );
}
