#!/usr/bin/env python3
# sync_email_tasks.py
# 同步邮件轮询任务到 Celery Beat
#
# 功能说明：
# 1. 扫描数据库中所有启用的邮箱账户
# 2. 为每个账户在 Celery Beat 中创建定时任务
# 3. 删除已禁用账户的任务
#
# 使用方法：
#   cd backend
#   source venv/bin/activate
#   python sync_email_tasks.py

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.email_worker_service import email_worker_service
from app.core.logging import setup_logging, get_logger

# 初始化日志
setup_logging()
logger = get_logger(__name__)


async def main():
    """主函数"""
    print("=" * 50)
    print("  邮件轮询任务同步工具")
    print("=" * 50)
    print()

    try:
        # 执行同步
        print("正在同步邮件轮询任务...")
        stats = await email_worker_service.sync_email_tasks()

        print()
        print("✅ 同步完成")
        print()
        print(f"  新增任务: {stats['added']}")
        print(f"  删除任务: {stats['removed']}")
        print(f"  更新任务: {stats['updated']}")
        print(f"  总计任务: {stats['total']}")
        print()

        if stats['total'] > 0:
            print("邮件轮询任务已配置，Celery Beat 将每 60 秒轮询一次")
            print()
            print("查看任务状态:")
            print("  - Flower 监控面板: http://localhost:5555")
            print("  - Celery 日志: tail -f logs/celery-beat.log")
        else:
            print("⚠️  没有配置邮箱账户")
            print()
            print("请在管理后台添加邮箱账户:")
            print("  http://localhost:3000/admin/settings")
            print()
            print("或者使用 API:")
            print("  POST /admin/email-accounts")

        print()
        return 0

    except Exception as e:
        logger.error(f"同步失败: {e}", exc_info=True)
        print()
        print(f"❌ 同步失败: {e}")
        print()
        print("请检查:")
        print("  1. PostgreSQL 是否运行: docker compose ps")
        print("  2. Redis 是否运行: docker compose ps")
        print("  3. 数据库连接配置: cat .env | grep DATABASE_URL")
        print()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
