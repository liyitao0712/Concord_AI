#!/usr/bin/env python3
# 测试本地存储功能

import asyncio
import sys
import os

# 添加 backend 到路径
sys.path.insert(0, '/Users/alexli/Concord_AI/backend')

async def test_local_storage():
    """测试本地存储功能"""
    print("=" * 60)
    print("测试本地存储功能")
    print("=" * 60)

    from app.storage.local_file import local_storage

    # 1. 测试初始化
    print("\n[1] 测试初始化...")
    success = local_storage.connect()
    print(f"   初始化结果: {'✅ 成功' if success else '❌ 失败'}")

    if not success:
        print("   本地存储未启用，跳过测试")
        return

    # 2. 测试上传
    print("\n[2] 测试上传...")
    test_content = b"This is a test email content"
    test_key = "test/emails/test.txt"

    try:
        url = await local_storage.upload(
            key=test_key,
            data=test_content,
            content_type="text/plain"
        )
        print(f"   上传成功: {url}")
    except Exception as e:
        print(f"   ❌ 上传失败: {e}")
        return

    # 3. 测试文件存在性
    print("\n[3] 测试文件存在性...")
    exists = await local_storage.exists(test_key)
    print(f"   文件存在: {'✅ 是' if exists else '❌ 否'}")

    # 4. 测试下载
    print("\n[4] 测试下载...")
    try:
        downloaded = await local_storage.download(test_key)
        if downloaded == test_content:
            print(f"   ✅ 下载成功，内容一致 ({len(downloaded)} bytes)")
        else:
            print(f"   ❌ 内容不一致")
    except Exception as e:
        print(f"   ❌ 下载失败: {e}")

    # 5. 测试元信息
    print("\n[5] 测试元信息...")
    meta = await local_storage.get_object_meta(test_key)
    if meta:
        print(f"   ✅ 获取成功:")
        print(f"      大小: {meta['size']} bytes")
        print(f"      类型: {meta['content_type']}")
    else:
        print(f"   ❌ 获取失败")

    # 6. 测试签名 URL
    print("\n[6] 测试签名 URL...")
    signed_url = local_storage.get_signed_url(test_key, expires=3600)
    print(f"   签名 URL: {signed_url}")

    # 7. 测试删除
    print("\n[7] 测试删除...")
    success = await local_storage.delete(test_key)
    print(f"   删除结果: {'✅ 成功' if success else '❌ 失败'}")

    # 验证删除
    exists = await local_storage.exists(test_key)
    print(f"   文件是否存在: {'❌ 仍存在' if exists else '✅ 已删除'}")

    print("\n" + "=" * 60)
    print("本地存储测试完成！")
    print("=" * 60)


async def test_email_persistence():
    """测试邮件持久化（OSS降级到本地）"""
    print("\n\n" + "=" * 60)
    print("测试邮件持久化（OSS降级）")
    print("=" * 60)

    from app.storage.email_persistence import persistence_service
    from app.storage.email import EmailMessage
    from datetime import datetime

    # 创建测试邮件
    test_email = EmailMessage(
        message_id="<test@example.com>",
        sender="test@example.com",
        sender_name="Test Sender",
        recipients=["recipient@example.com"],
        subject="Test Email",
        body_text="This is a test email body with some content.",
        body_html="<html><body>Test</body></html>",
        date=datetime.now(),
        raw_bytes=b"From: test@example.com\r\nSubject: Test\r\n\r\nTest body",
    )

    print("\n[1] 测试持久化...")
    try:
        record = await persistence_service.persist(test_email, account_id=None)
        print(f"   ✅ 持久化成功:")
        print(f"      记录 ID: {record.id}")
        print(f"      存储类型: {record.storage_type}")
        print(f"      存储路径: {record.oss_key}")
        print(f"      邮件大小: {record.size_bytes} bytes")
        print(f"      正文长度: {len(record.body_text)} 字符")

        # 验证完整正文
        if len(record.body_text) == len(test_email.body_text):
            print(f"      ✅ 完整正文已保存（不再截断）")
        else:
            print(f"      ⚠️  正文被截断: {len(record.body_text)}/{len(test_email.body_text)}")

        # 清理测试数据
        print("\n[2] 清理测试数据...")
        from app.core.database import async_session_maker
        from app.models.email_raw import EmailRawMessage
        from sqlalchemy import delete

        async with async_session_maker() as session:
            stmt = delete(EmailRawMessage).where(EmailRawMessage.id == record.id)
            await session.execute(stmt)
            await session.commit()

        # 删除文件
        if record.storage_type == "local":
            from app.storage.local_file import local_storage
            await local_storage.delete(record.oss_key)

        print(f"   ✅ 清理完成")

    except Exception as e:
        print(f"   ❌ 持久化失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("邮件持久化测试完成！")
    print("=" * 60)


async def main():
    """主测试函数"""
    await test_local_storage()
    await test_email_persistence()


if __name__ == "__main__":
    asyncio.run(main())
