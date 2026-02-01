#!/usr/bin/env python3
# scripts/create_admin.py
# 创建初始管理员账户脚本
#
# 功能说明：
# 1. 创建第一个管理员账户
# 2. 如果已有管理员则跳过
# 3. 支持命令行参数指定账户信息
#
# 使用方法：
#   # 使用默认值创建
#   python scripts/create_admin.py
#
#   # 指定参数创建
#   python scripts/create_admin.py --email admin@example.com --password mypassword --name 管理员
#
# 默认账户：
#   邮箱: admin@concordai.com
#   密码: admin123456
#   名称: 系统管理员

import asyncio
import argparse
import sys
import os

# 将 backend 目录添加到 Python 路径
# 这样才能正确导入 app 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine, Base
from app.core.security import hash_password
from app.models.user import User


async def create_admin(email: str, password: str, name: str):
    """
    创建管理员账户

    Args:
        email: 管理员邮箱
        password: 管理员密码
        name: 管理员名称
    """
    # 创建数据库会话
    async with AsyncSession(engine) as session:
        # 检查是否已有管理员
        result = await session.execute(
            select(User).where(User.role == "admin")
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print(f"⚠️  已存在管理员账户: {existing_admin.email}")
            print("   如需创建新管理员，请先删除现有管理员或使用管理员后台创建")
            return False

        # 检查邮箱是否已被使用
        result = await session.execute(
            select(User).where(User.email == email)
        )
        if result.scalar_one_or_none():
            print(f"❌ 邮箱已被使用: {email}")
            return False

        # 创建管理员
        admin = User(
            email=email,
            password_hash=hash_password(password),
            name=name,
            role="admin",
            is_active=True
        )

        session.add(admin)
        await session.commit()

        print("✅ 管理员账户创建成功！")
        print(f"   邮箱: {email}")
        print(f"   名称: {name}")
        print(f"   角色: admin")
        print("")
        print("🔐 请妥善保管密码，首次登录后建议修改密码")
        return True


def main():
    """
    主函数：解析命令行参数并创建管理员
    """
    parser = argparse.ArgumentParser(
        description="创建 Concord AI 系统管理员账户",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/create_admin.py
  python scripts/create_admin.py --email admin@example.com --password mypassword
  python scripts/create_admin.py -e admin@example.com -p mypassword -n 管理员
        """
    )

    parser.add_argument(
        "-e", "--email",
        default="admin@concordai.com",
        help="管理员邮箱（默认: admin@concordai.com）"
    )

    parser.add_argument(
        "-p", "--password",
        default="admin123456",
        help="管理员密码（默认: admin123456）"
    )

    parser.add_argument(
        "-n", "--name",
        default="系统管理员",
        help="管理员名称（默认: 系统管理员）"
    )

    args = parser.parse_args()

    # 密码长度验证
    if len(args.password) < 6:
        print("❌ 密码长度至少 6 位")
        sys.exit(1)

    print("=" * 50)
    print("   Concord AI - 创建管理员账户")
    print("=" * 50)
    print(f"邮箱: {args.email}")
    print(f"名称: {args.name}")
    print("=" * 50)
    print("")

    # 运行异步函数
    success = asyncio.run(create_admin(
        email=args.email,
        password=args.password,
        name=args.name
    ))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
