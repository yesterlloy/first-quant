"""初始化默认用户脚本.

首次部署时运行此脚本创建默认管理员账号。
默认账号：admin / admin123

用法：
    cd backend
    python scripts/init_default_user.py
"""

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.database import SessionLocal  # noqa: E402
from app.schemas.user import UserCreate  # noqa: E402
from app.services import auth_service  # noqa: E402

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"
DEFAULT_EMAIL = "admin@example.com"
DEFAULT_FULL_NAME = "管理员"


def main():
    """创建默认用户."""
    # 先初始化数据库表
    from app.core.database import init_db

    init_db()

    db = SessionLocal()
    try:
        # 检查用户是否已存在
        existing_user = auth_service.get_user_by_username(db, DEFAULT_USERNAME)
        if existing_user:
            print(f"⚠️  用户 '{DEFAULT_USERNAME}' 已存在，跳过创建")
            print(f"   用户名: {DEFAULT_USERNAME}")
            return

        # 创建默认用户
        user_in = UserCreate(
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD,
            email=DEFAULT_EMAIL,
            full_name=DEFAULT_FULL_NAME,
        )
        user = auth_service.register_user(db, user_in)

        print("✅ 默认用户创建成功！")
        print(f"   用户名: {DEFAULT_USERNAME}")
        print(f"   密码: {DEFAULT_PASSWORD}")
        print(f"   姓名: {user.full_name}")
        print(f"   邮箱: {user.email}")
        print("\n⚠️  请在首次登录后修改默认密码！")

    except Exception as e:  # noqa: BLE001
        print(f"❌ 创建用户失败: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
