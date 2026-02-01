#!/usr/bin/env python3
# 简单测试 - 验证代码语法和导入

import sys
sys.path.insert(0, '/Users/alexli/Concord_AI/backend')

print("=" * 60)
print("测试代码导入和语法")
print("=" * 60)

# 1. 测试本地存储类导入
print("\n[1] 测试本地存储类导入...")
try:
    from app.storage.local_file import LocalFileStorage, local_storage
    print("   ✅ LocalFileStorage 导入成功")
    print(f"   类路径: {LocalFileStorage.__module__}.{LocalFileStorage.__name__}")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")

# 2. 测试邮箱服务导入
print("\n[2] 测试邮箱服务导入...")
try:
    from app.services.email_account_service import EmailAccountService, email_account_service
    print("   ✅ EmailAccountService 导入成功")
    print(f"   类路径: {EmailAccountService.__module__}.{EmailAccountService.__name__}")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")

# 3. 测试数据模型
print("\n[3] 测试数据模型...")
try:
    from app.models.email_raw import EmailRawMessage, EmailAttachment

    # 检查字段
    has_storage_type = hasattr(EmailRawMessage, 'storage_type')
    print(f"   EmailRawMessage.storage_type: {'✅ 存在' if has_storage_type else '❌ 不存在'}")

    has_att_storage = hasattr(EmailAttachment, 'storage_type')
    print(f"   EmailAttachment.storage_type: {'✅ 存在' if has_att_storage else '❌ 不存在'}")

except Exception as e:
    print(f"   ❌ 测试失败: {e}")

# 4. 测试持久化服务
print("\n[4] 测试持久化服务修改...")
try:
    from app.storage.email_persistence import persistence_service, StorageBackend
    print(f"   ✅ persistence_service 导入成功")
    print(f"   StorageBackend.OSS: {StorageBackend.OSS}")
    print(f"   StorageBackend.LOCAL: {StorageBackend.LOCAL}")

    # 检查方法
    has_upload_file = hasattr(persistence_service, '_upload_file')
    print(f"   _upload_file 方法: {'✅ 存在' if has_upload_file else '❌ 不存在'}")

    has_delete_file = hasattr(persistence_service, '_delete_file')
    print(f"   _delete_file 方法: {'✅ 存在' if has_delete_file else '❌ 不存在'}")

except Exception as e:
    print(f"   ❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 测试 API 修改
print("\n[5] 测试 API 修改...")
try:
    # 只检查语法，不实际运行
    with open('/Users/alexli/Concord_AI/backend/app/api/email_accounts.py', 'r') as f:
        content = f.read()

    has_cascade_delete = 'delete_account_cascade' in content
    print(f"   级联删除调用: {'✅ 存在' if has_cascade_delete else '❌ 不存在'}")

    has_stats_endpoint = '/stats' in content
    print(f"   统计端点: {'✅ 存在' if has_stats_endpoint else '❌ 不存在'}")

    has_service_import = 'email_account_service' in content
    print(f"   服务导入: {'✅ 存在' if has_service_import else '❌ 不存在'}")

except Exception as e:
    print(f"   ❌ 检查失败: {e}")

print("\n" + "=" * 60)
print("代码检查完成！")
print("=" * 60)
