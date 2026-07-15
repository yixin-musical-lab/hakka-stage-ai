import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException, Response
from jwt import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes.auth import create_account, create_accounts_batch, login, update_my_password
from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import (
    AccountCreateRequest,
    BatchAccountCreateRequest,
    LoginRequest,
    PasswordChangeRequest,
)
from app.services.auth_service import create_user, find_user_by_email
from app.services.account_bootstrap import ensure_bootstrap_account


class AuthSchemaTests(unittest.TestCase):
    """验证账号创建、批量 JSON 和改密请求的核心规则。"""

    def test_account_create_normalizes_email_and_display_name(self):
        request = AccountCreateRequest(
            email="  Teacher@Example.COM ",
            password="course2026",
            display_name="  林老师  ",
            role="teacher",
        )

        self.assertEqual(str(request.email), "teacher@example.com")
        self.assertEqual(request.display_name, "林老师")

    def test_password_requires_letters_and_numbers(self):
        with self.assertRaises(ValidationError):
            AccountCreateRequest(email="teacher@example.com", password="onlyletters", display_name="林老师")
        with self.assertRaises(ValidationError):
            PasswordChangeRequest(current_password="old12345", new_password="12345678")

    def test_batch_rejects_duplicate_emails_before_database_write(self):
        account = {
            "email": "student@example.com",
            "password": "student2026",
            "display_name": "学生一",
            "role": "student",
        }
        with self.assertRaises(ValidationError):
            BatchAccountCreateRequest(accounts=[account, {**account, "email": "STUDENT@example.com"}])


class AuthSecurityTests(unittest.TestCase):
    """验证密码不会明文保存，JWT 只能由对应密钥解码。"""

    def test_password_hash_round_trip(self):
        hashed = hash_password("course2026")

        self.assertNotEqual(hashed, "course2026")
        self.assertTrue(verify_password("course2026", hashed))
        self.assertFalse(verify_password("wrong2026", hashed))

    def test_access_token_contains_user_and_rejects_wrong_secret(self):
        user_id = uuid4()
        settings = Settings(auth_secret_key="unit-test-secret-at-least-32-bytes", auth_access_token_minutes=30)
        token, expires_in = create_access_token(user_id, settings)

        self.assertEqual(expires_in, 1800)
        self.assertEqual(decode_access_token(token, settings), user_id)
        with self.assertRaises(InvalidTokenError):
            decode_access_token(token, Settings(auth_secret_key="different-secret-at-least-32-bytes"))


class AuthDatabaseFlowTests(unittest.TestCase):
    """使用内存数据库验证登录后创建、批量原子写入和改密主链路。"""

    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        User.__table__.create(bind=self.engine)
        self.db = sessionmaker(bind=self.engine, expire_on_commit=False)()
        # 首个账号由服务端引导创建，之后的 HTTP 创建接口都必须带当前登录用户。
        self.creator = create_user(
            self.db,
            AccountCreateRequest(
                email="creator@example.com",
                password="course2026",
                display_name="账号创建人",
                role="teacher",
            ),
        )

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_login_single_create_duplicate_and_password_change(self):
        login_response = Response()
        session = login(
            LoginRequest(email="creator@example.com", password="course2026"),
            login_response,
            self.db,
        )
        self.assertEqual(session.user.id, self.creator.id)
        self.assertIn("hakka_access_token=", login_response.headers["set-cookie"])

        created = create_account(
            AccountCreateRequest(
                email="student@example.com",
                password="student2026",
                display_name="学生一",
                role="student",
            ),
            self.creator,
            self.db,
        )
        self.assertEqual(str(created.email), "student@example.com")

        with self.assertRaises(HTTPException) as duplicate_context:
            create_account(
                AccountCreateRequest(
                    email="STUDENT@example.com",
                    password="another2026",
                    display_name="学生二",
                ),
                self.creator,
                self.db,
            )
        self.assertEqual(duplicate_context.exception.status_code, 409)

        update_my_password(
            PasswordChangeRequest(current_password="course2026", new_password="newcourse2026"),
            self.creator,
            self.db,
        )
        with self.assertRaises(HTTPException):
            login(LoginRequest(email="creator@example.com", password="course2026"), Response(), self.db)
        self.assertEqual(
            login(LoginRequest(email="creator@example.com", password="newcourse2026"), Response(), self.db).user.id,
            self.creator.id,
        )

    def test_batch_create_is_atomic_when_any_email_exists(self):
        successful = create_accounts_batch(
            BatchAccountCreateRequest(
                accounts=[
                    {
                        "email": "student02@example.com",
                        "password": "student2026",
                        "display_name": "学生二",
                        "role": "student",
                    },
                    {
                        "email": "teacher02@example.com",
                        "password": "teacher2026",
                        "display_name": "李老师",
                        "role": "teacher",
                    },
                ]
            ),
            self.creator,
            self.db,
        )
        self.assertEqual(successful.created_count, 2)

        with self.assertRaises(HTTPException) as conflict_context:
            create_accounts_batch(
                BatchAccountCreateRequest(
                    accounts=[
                        {
                            "email": "never-created@example.com",
                            "password": "student2026",
                            "display_name": "不会创建",
                            "role": "student",
                        },
                        {
                            "email": "student02@example.com",
                            "password": "student2026",
                            "display_name": "重复账号",
                            "role": "student",
                        },
                    ]
                ),
                self.creator,
                self.db,
            )
        self.assertEqual(conflict_context.exception.status_code, 409)
        self.assertIsNone(find_user_by_email(self.db, "never-created@example.com"))


class AccountBootstrapTests(unittest.TestCase):
    """验证全新数据库只能通过服务端配置创建一次首账号。"""

    def test_bootstrap_creates_only_when_user_table_is_empty(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        User.__table__.create(bind=engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        settings = Settings(
            bootstrap_account_email="initial@example.com",
            bootstrap_account_password="initial2026",
            bootstrap_account_display_name="初始老师",
            bootstrap_account_role="teacher",
        )

        with (
            patch("app.services.account_bootstrap.SessionLocal", session_factory),
            patch("app.services.account_bootstrap.get_settings", return_value=settings),
        ):
            self.assertTrue(ensure_bootstrap_account())
            self.assertFalse(ensure_bootstrap_account())

        with session_factory() as db:
            account = find_user_by_email(db, "initial@example.com")
            self.assertIsNotNone(account)
            self.assertTrue(verify_password("initial2026", account.password_hash))
        engine.dispose()


class AuthOpenApiTests(unittest.TestCase):
    """确保匿名注册消失，账号创建接口清晰声明 Bearer 鉴权。"""

    def test_openapi_exposes_authenticated_account_creation_only(self):
        from app.main import app

        schema = app.openapi()
        paths = schema["paths"]
        self.assertNotIn("/api/auth/register", paths)
        self.assertIn("post", paths["/api/auth/login"])
        self.assertIn("post", paths["/api/auth/logout"])
        self.assertIn("post", paths["/api/accounts"])
        self.assertIn("post", paths["/api/accounts/batch"])
        self.assertIn("get", paths["/api/account/me"])
        self.assertIn("patch", paths["/api/account/profile"])
        self.assertIn("post", paths["/api/account/password"])

        self.assertNotIn("security", paths["/api/auth/login"]["post"])
        self.assertEqual(paths["/api/accounts"]["post"]["security"], [{"BearerAuth": []}])
        self.assertEqual(paths["/api/accounts/batch"]["post"]["security"], [{"BearerAuth": []}])


if __name__ == "__main__":
    unittest.main()
