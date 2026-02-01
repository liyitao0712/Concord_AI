#!/usr/bin/env python3
"""
迁移飞书配置到 Worker

将 system_settings 表中的飞书配置迁移到 worker_configs 表

使用方法：
    cd backend
    source venv/bin/activate
    python ../scripts/migrate_feishu_to_workers.py
"""

import asyncio
import sys
import os

# 添加后端目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select, delete
from app.core.database import async_session_maker
from app.models.settings import SystemSetting
from app.models.worker import WorkerConfig


async def migrate():
    """执行迁移"""
    print("=" * 60)
    print("飞书配置迁移工具")
    print("=" * 60)
    print()

    async with async_session_maker() as db:
        # 1. 读取现有的飞书配置
        print("[1/4] 读取现有飞书配置...")

        result = await db.execute(
            select(SystemSetting).where(SystemSetting.category == "feishu")
        )
        settings = result.scalars().all()

        if not settings:
            print("  没有找到飞书配置，跳过迁移")
            return

        # 解析配置
        config_dict = {}
        for setting in settings:
            key = setting.key.replace("feishu.", "")
            config_dict[key] = setting.value
            print(f"  找到: {setting.key} = {'***' if 'secret' in key else setting.value}")

        # 检查是否有有效配置
        app_id = config_dict.get("app_id", "")
        app_secret = config_dict.get("app_secret", "")
        enabled = config_dict.get("enabled", "false") == "true"

        if not app_id:
            print("  App ID 为空，跳过迁移")
            return

        print()

        # 2. 检查是否已存在相同配置
        print("[2/4] 检查是否已迁移...")

        result = await db.execute(
            select(WorkerConfig).where(WorkerConfig.worker_type == "feishu")
        )
        existing_workers = result.scalars().all()

        # 手动检查 app_id
        existing = None
        for w in existing_workers:
            if w.config.get("app_id") == app_id:
                existing = w
                break

        if existing:
            print(f"  已存在相同配置: {existing.name} (ID: {existing.id})")
            print("  跳过创建，但会删除旧配置")
        else:
            # 3. 创建新的 Worker 配置
            print("[3/4] 创建 Worker 配置...")

            worker_config = WorkerConfig(
                worker_type="feishu",
                name="飞书机器人（迁移）",
                config={
                    "app_id": app_id,
                    "app_secret": app_secret,
                    "encrypt_key": config_dict.get("encrypt_key", ""),
                    "verification_token": config_dict.get("verification_token", ""),
                },
                agent_id="chat_agent",
                is_enabled=enabled,
                description="从 system_settings 迁移的配置",
            )

            db.add(worker_config)
            await db.flush()

            print(f"  创建成功: {worker_config.name}")
            print(f"  ID: {worker_config.id}")
            print(f"  启用: {worker_config.is_enabled}")

        print()

        # 4. 删除旧配置（可选）
        print("[4/4] 清理旧配置...")

        confirm = input("  是否删除 system_settings 中的飞书配置？[y/N] ").strip().lower()

        if confirm == "y":
            await db.execute(
                delete(SystemSetting).where(SystemSetting.category == "feishu")
            )
            print("  已删除旧配置")
        else:
            print("  保留旧配置")

        await db.commit()

        print()
        print("=" * 60)
        print("迁移完成！")
        print()
        print("后续步骤：")
        print("1. 访问 http://localhost:3000/admin/workers 查看新配置")
        print("2. 重启后端服务使新配置生效")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(migrate())
