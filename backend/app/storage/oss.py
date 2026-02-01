# app/storage/oss.py
# 阿里云 OSS 文件存储模块
#
# 功能说明：
# 1. 上传文件到 OSS
# 2. 下载文件从 OSS
# 3. 删除 OSS 文件
# 4. 生成临时访问链接（带签名）
# 5. 检查文件是否存在
#
# 使用方法：
#   from app.storage.oss import oss_client
#
#   # 上传文件
#   url = await oss_client.upload("documents/test.pdf", file_content)
#
#   # 下载文件
#   content = await oss_client.download("documents/test.pdf")
#
#   # 生成临时链接（1小时有效）
#   url = oss_client.get_signed_url("documents/test.pdf", expires=3600)
#
# 注意事项：
# - 需要安装 oss2 库：pip install oss2
# - 需要配置环境变量：OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_ENDPOINT, OSS_BUCKET
# - 生产环境建议使用 RAM 子账号，不要使用主账号 AK

import asyncio
from typing import Optional, BinaryIO, Union
from datetime import datetime
import mimetypes

import oss2
from oss2.exceptions import OssError, NoSuchKey

from app.core.config import settings
from app.core.logging import get_logger

# 获取当前模块的 logger
logger = get_logger(__name__)


class OSSClient:
    """
    阿里云 OSS 客户端封装

    这个类封装了阿里云 OSS 的常用操作，提供简单易用的接口。

    设计说明：
    - 使用单例模式，全局共享一个客户端实例
    - 所有操作都包装成异步方法，避免阻塞事件循环
    - 提供完善的错误处理和日志记录

    属性说明：
    - auth: OSS 认证对象，包含 Access Key
    - bucket: OSS Bucket 对象，所有操作都通过它进行
    - _initialized: 标记是否已初始化
    """

    def __init__(self):
        """
        初始化 OSS 客户端

        注意：实际的连接在 connect() 方法中建立
        这样可以在配置缺失时延迟报错
        """
        self.auth = None
        self.bucket = None
        self._initialized = False
        self._endpoint = None
        self._bucket_name = None

    def connect(self) -> bool:
        """
        建立 OSS 连接

        这个方法会：
        1. 优先从数据库读取配置，否则使用环境变量
        2. 检查必要的配置是否存在
        3. 创建认证对象
        4. 创建 Bucket 对象

        Returns:
            bool: 连接是否成功

        使用示例：
            if oss_client.connect():
                print("OSS 连接成功")
        """
        # 获取配置（优先数据库，其次环境变量）
        config = self._get_config()

        access_key_id = config.get("access_key_id")
        access_key_secret = config.get("access_key_secret")
        endpoint = config.get("endpoint")
        bucket = config.get("bucket")

        # 检查必要配置
        if not access_key_id:
            logger.warning("OSS_ACCESS_KEY_ID 未配置，OSS 功能不可用")
            return False

        if not access_key_secret:
            logger.warning("OSS_ACCESS_KEY_SECRET 未配置，OSS 功能不可用")
            return False

        if not bucket:
            logger.warning("OSS_BUCKET 未配置，OSS 功能不可用")
            return False

        if not endpoint:
            logger.warning("OSS_ENDPOINT 未配置，OSS 功能不可用")
            return False

        try:
            # 创建认证对象
            self.auth = oss2.Auth(access_key_id, access_key_secret)

            # 创建 Bucket 对象
            self.bucket = oss2.Bucket(self.auth, endpoint, bucket)

            # 保存配置用于生成 URL
            self._endpoint = endpoint
            self._bucket_name = bucket

            self._initialized = True
            logger.info(f"OSS 连接成功: {bucket}")
            return True

        except Exception as e:
            logger.error(f"OSS 连接失败: {e}")
            return False

    def _get_config(self) -> dict:
        """
        获取 OSS 配置

        优先从数据库读取，如果没有则使用环境变量

        Returns:
            dict: 包含 access_key_id, access_key_secret, endpoint, bucket
        """
        # 尝试从数据库读取
        try:
            from app.core.database import sync_session_maker
            from app.models.settings import SystemSetting
            from sqlalchemy import select

            config = {}
            with sync_session_maker() as session:
                for key in ["access_key_id", "access_key_secret", "endpoint", "bucket"]:
                    result = session.execute(
                        select(SystemSetting).where(SystemSetting.key == f"oss.{key}")
                    )
                    setting = result.scalar_one_or_none()
                    if setting:
                        config[key] = setting.value

            # 如果数据库有完整配置，使用数据库配置
            if all(config.get(k) for k in ["access_key_id", "access_key_secret", "endpoint", "bucket"]):
                logger.debug("使用数据库 OSS 配置")
                return config

        except Exception as e:
            logger.debug(f"从数据库读取 OSS 配置失败，使用环境变量: {e}")

        # 回退到环境变量
        return {
            "access_key_id": getattr(settings, "OSS_ACCESS_KEY_ID", None),
            "access_key_secret": getattr(settings, "OSS_ACCESS_KEY_SECRET", None),
            "endpoint": getattr(settings, "OSS_ENDPOINT", None),
            "bucket": getattr(settings, "OSS_BUCKET", None),
        }

    def _ensure_connected(self) -> None:
        """
        确保 OSS 已连接

        这是一个内部方法，在每次操作前调用
        如果未连接则尝试连接，连接失败则抛出异常

        Raises:
            RuntimeError: 如果 OSS 未配置或连接失败
        """
        if not self._initialized:
            if not self.connect():
                raise RuntimeError("OSS 未配置或连接失败")

    async def upload(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None
    ) -> str:
        """
        上传文件到 OSS

        Args:
            key: 文件在 OSS 中的路径（Object Key）
                 例如: "documents/2024/report.pdf"
            data: 文件内容，可以是 bytes 或文件对象
            content_type: 文件 MIME 类型，如 "application/pdf"
                          如果不指定，会根据文件扩展名自动推断

        Returns:
            str: 文件的完整 URL（不带签名，公开访问需要 Bucket 设置为公共读）

        Raises:
            RuntimeError: OSS 未连接
            OssError: OSS 操作失败

        使用示例：
            # 上传 bytes
            url = await oss_client.upload("test.txt", b"Hello World")

            # 上传文件对象
            with open("local.pdf", "rb") as f:
                url = await oss_client.upload("remote.pdf", f)
        """
        self._ensure_connected()

        # 自动推断 Content-Type
        if content_type is None:
            content_type, _ = mimetypes.guess_type(key)
            if content_type is None:
                content_type = "application/octet-stream"

        # 设置请求头
        headers = {
            "Content-Type": content_type
        }

        try:
            # 使用 asyncio.to_thread 将同步操作放到线程池执行
            # 这样不会阻塞事件循环
            await asyncio.to_thread(
                self.bucket.put_object,
                key,
                data,
                headers=headers
            )

            # 构建文件 URL
            url = f"https://{self._bucket_name}.{self._endpoint}/{key}"

            logger.info(f"文件上传成功: {key}")
            return url

        except OssError as e:
            logger.error(f"文件上传失败: {key}, 错误: {e}")
            raise

    async def upload_file(
        self,
        key: str,
        local_path: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        上传本地文件到 OSS

        这是 upload() 的便捷方法，直接指定本地文件路径

        Args:
            key: 文件在 OSS 中的路径
            local_path: 本地文件路径
            content_type: 文件 MIME 类型

        Returns:
            str: 文件的完整 URL

        使用示例：
            url = await oss_client.upload_file(
                "documents/report.pdf",
                "/tmp/report.pdf"
            )
        """
        self._ensure_connected()

        # 自动推断 Content-Type
        if content_type is None:
            content_type, _ = mimetypes.guess_type(local_path)
            if content_type is None:
                content_type = "application/octet-stream"

        headers = {"Content-Type": content_type}

        try:
            await asyncio.to_thread(
                self.bucket.put_object_from_file,
                key,
                local_path,
                headers=headers
            )

            url = f"https://{self._bucket_name}.{self._endpoint}/{key}"
            logger.info(f"文件上传成功: {key} <- {local_path}")
            return url

        except OssError as e:
            logger.error(f"文件上传失败: {key}, 错误: {e}")
            raise

    async def download(self, key: str) -> bytes:
        """
        从 OSS 下载文件

        Args:
            key: 文件在 OSS 中的路径

        Returns:
            bytes: 文件内容

        Raises:
            NoSuchKey: 文件不存在
            OssError: OSS 操作失败

        使用示例：
            content = await oss_client.download("documents/test.pdf")
            with open("local.pdf", "wb") as f:
                f.write(content)
        """
        self._ensure_connected()

        try:
            # 获取文件对象
            result = await asyncio.to_thread(
                self.bucket.get_object,
                key
            )

            # 读取全部内容
            content = await asyncio.to_thread(result.read)

            logger.info(f"文件下载成功: {key}, 大小: {len(content)} bytes")
            return content

        except NoSuchKey:
            logger.warning(f"文件不存在: {key}")
            raise
        except OssError as e:
            logger.error(f"文件下载失败: {key}, 错误: {e}")
            raise

    async def download_to_file(self, key: str, local_path: str) -> None:
        """
        从 OSS 下载文件到本地

        Args:
            key: 文件在 OSS 中的路径
            local_path: 本地保存路径

        使用示例：
            await oss_client.download_to_file(
                "documents/report.pdf",
                "/tmp/report.pdf"
            )
        """
        self._ensure_connected()

        try:
            await asyncio.to_thread(
                self.bucket.get_object_to_file,
                key,
                local_path
            )
            logger.info(f"文件下载成功: {key} -> {local_path}")

        except NoSuchKey:
            logger.warning(f"文件不存在: {key}")
            raise
        except OssError as e:
            logger.error(f"文件下载失败: {key}, 错误: {e}")
            raise

    async def delete(self, key: str) -> bool:
        """
        删除 OSS 文件

        Args:
            key: 文件在 OSS 中的路径

        Returns:
            bool: 是否删除成功（文件不存在也返回 True）

        使用示例：
            success = await oss_client.delete("documents/old.pdf")
        """
        self._ensure_connected()

        try:
            await asyncio.to_thread(
                self.bucket.delete_object,
                key
            )
            logger.info(f"文件删除成功: {key}")
            return True

        except OssError as e:
            logger.error(f"文件删除失败: {key}, 错误: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        检查文件是否存在

        Args:
            key: 文件在 OSS 中的路径

        Returns:
            bool: 文件是否存在

        使用示例：
            if await oss_client.exists("documents/test.pdf"):
                print("文件存在")
        """
        self._ensure_connected()

        try:
            result = await asyncio.to_thread(
                self.bucket.object_exists,
                key
            )
            return result

        except OssError as e:
            logger.error(f"检查文件存在失败: {key}, 错误: {e}")
            return False

    def get_signed_url(
        self,
        key: str,
        expires: int = 3600,
        method: str = "GET"
    ) -> str:
        """
        生成带签名的临时访问 URL

        签名 URL 可以让没有 OSS 权限的用户临时访问私有文件
        URL 在指定时间后自动失效

        Args:
            key: 文件在 OSS 中的路径
            expires: URL 有效期（秒），默认 3600（1小时）
            method: HTTP 方法，GET（下载）或 PUT（上传）

        Returns:
            str: 带签名的临时 URL

        使用示例：
            # 生成 1 小时有效的下载链接
            url = oss_client.get_signed_url("documents/private.pdf")

            # 生成 5 分钟有效的上传链接
            upload_url = oss_client.get_signed_url(
                "uploads/new.pdf",
                expires=300,
                method="PUT"
            )
        """
        self._ensure_connected()

        url = self.bucket.sign_url(method, key, expires)
        logger.debug(f"生成签名 URL: {key}, 有效期: {expires}秒")
        return url

    async def list_objects(
        self,
        prefix: str = "",
        max_keys: int = 100
    ) -> list[dict]:
        """
        列出 OSS 中的文件

        Args:
            prefix: 路径前缀，用于筛选特定目录下的文件
                    例如: "documents/2024/" 只列出该目录下的文件
            max_keys: 最多返回的文件数量

        Returns:
            list[dict]: 文件列表，每个文件包含 key、size、last_modified

        使用示例：
            # 列出 documents 目录下的文件
            files = await oss_client.list_objects("documents/")
            for f in files:
                print(f"{f['key']}: {f['size']} bytes")
        """
        self._ensure_connected()

        try:
            result = await asyncio.to_thread(
                oss2.ObjectIterator,
                self.bucket,
                prefix=prefix,
                max_keys=max_keys
            )

            files = []
            for obj in result:
                files.append({
                    "key": obj.key,
                    "size": obj.size,
                    "last_modified": obj.last_modified
                })

            return files

        except OssError as e:
            logger.error(f"列出文件失败: {prefix}, 错误: {e}")
            return []

    async def get_object_meta(self, key: str) -> Optional[dict]:
        """
        获取文件元信息

        Args:
            key: 文件在 OSS 中的路径

        Returns:
            dict: 文件元信息，包含 size、content_type、last_modified 等
                  如果文件不存在返回 None

        使用示例：
            meta = await oss_client.get_object_meta("documents/test.pdf")
            if meta:
                print(f"文件大小: {meta['size']} bytes")
        """
        self._ensure_connected()

        try:
            result = await asyncio.to_thread(
                self.bucket.get_object_meta,
                key
            )

            return {
                "size": result.content_length,
                "content_type": result.content_type,
                "last_modified": result.last_modified,
                "etag": result.etag
            }

        except NoSuchKey:
            return None
        except OssError as e:
            logger.error(f"获取文件元信息失败: {key}, 错误: {e}")
            return None


# ==================== 全局单例 ====================

# 创建全局 OSS 客户端实例
# 使用方式：from app.storage.oss import oss_client
oss_client = OSSClient()


# ==================== 依赖注入 ====================

def get_oss_client() -> OSSClient:
    """
    获取 OSS 客户端（依赖注入用）

    在 FastAPI 路由中使用：
        @router.post("/upload")
        async def upload_file(
            oss: OSSClient = Depends(get_oss_client)
        ):
            ...

    Returns:
        OSSClient: OSS 客户端实例
    """
    if not oss_client._initialized:
        oss_client.connect()
    return oss_client
