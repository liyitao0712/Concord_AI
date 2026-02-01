# app/storage/local_file.py
# 本地文件存储模块
#
# 功能说明：
# 1. 提供与 OSS 兼容的本地文件存储接口
# 2. 当 OSS 未配置或失败时作为降级方案
# 3. 支持上传、下载、删除、生成临时访问链接
#
# 使用方法：
#   from app.storage.local_file import local_storage
#
#   # 上传文件
#   await local_storage.upload("emails/test.eml", file_content)
#
#   # 下载文件
#   content = await local_storage.download("emails/test.eml")
#
#   # 生成访问 URL
#   url = local_storage.get_url("emails/test.eml")

import os
import asyncio
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Union, BinaryIO
from datetime import datetime, timedelta
from urllib.parse import quote

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LocalFileStorage:
    """
    本地文件存储

    提供与 OSSClient 兼容的接口，用于 OSS 不可用时的降级存储。

    特点：
    - 文件存储在本地磁盘 (data/storage/ 目录)
    - 支持生成临时访问 URL（通过 token 验证）
    - 自动创建目录结构
    - 线程安全的异步操作
    """

    def __init__(self):
        """初始化本地存储"""
        self.base_path = Path(settings.LOCAL_STORAGE_PATH)
        self.enabled = settings.LOCAL_STORAGE_ENABLED
        self._initialized = False

        # 临时 URL token 存储（生产环境应该用 Redis）
        self._temp_tokens = {}

    def connect(self) -> bool:
        """
        初始化本地存储

        创建存储根目录

        Returns:
            bool: 是否初始化成功
        """
        if not self.enabled:
            logger.info("[LocalStorage] 本地存储未启用")
            return False

        try:
            # 创建根目录
            self.base_path.mkdir(parents=True, exist_ok=True)
            self._initialized = True
            logger.info(f"[LocalStorage] 本地存储初始化成功: {self.base_path.absolute()}")
            return True

        except Exception as e:
            logger.error(f"[LocalStorage] 初始化失败: {e}")
            return False

    def _ensure_connected(self) -> None:
        """确保已初始化"""
        if not self._initialized:
            if not self.connect():
                raise RuntimeError("本地存储未启用或初始化失败")

    def _get_file_path(self, key: str) -> Path:
        """
        获取文件的绝对路径

        Args:
            key: 文件相对路径

        Returns:
            Path: 文件绝对路径
        """
        # 防止路径穿越攻击
        safe_key = key.lstrip("/").replace("..", "")
        return self.base_path / safe_key

    async def upload(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None
    ) -> str:
        """
        上传文件到本地存储

        Args:
            key: 文件路径（相对于存储根目录）
            data: 文件内容
            content_type: MIME 类型（本地存储暂不使用）

        Returns:
            str: 文件 URL（本地路径）

        Raises:
            RuntimeError: 存储未初始化
            IOError: 文件写入失败
        """
        self._ensure_connected()

        file_path = self._get_file_path(key)

        # 创建父目录
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 异步写入文件
            if isinstance(data, bytes):
                await asyncio.to_thread(file_path.write_bytes, data)
            else:
                # 如果是文件对象，读取内容后写入
                content = await asyncio.to_thread(data.read)
                await asyncio.to_thread(file_path.write_bytes, content)

            logger.info(f"[LocalStorage] 文件上传成功: {key}")
            return f"local://{key}"

        except Exception as e:
            logger.error(f"[LocalStorage] 文件上传失败: {key}, {e}")
            raise

    async def upload_file(
        self,
        key: str,
        local_path: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        从本地文件上传到存储

        Args:
            key: 目标路径
            local_path: 源文件路径
            content_type: MIME 类型

        Returns:
            str: 文件 URL
        """
        self._ensure_connected()

        source = Path(local_path)
        if not source.exists():
            raise FileNotFoundError(f"源文件不存在: {local_path}")

        content = await asyncio.to_thread(source.read_bytes)
        return await self.upload(key, content, content_type)

    async def download(self, key: str) -> bytes:
        """
        从本地存储下载文件

        Args:
            key: 文件路径

        Returns:
            bytes: 文件内容

        Raises:
            FileNotFoundError: 文件不存在
        """
        self._ensure_connected()

        file_path = self._get_file_path(key)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {key}")

        try:
            content = await asyncio.to_thread(file_path.read_bytes)
            logger.info(f"[LocalStorage] 文件下载成功: {key}, 大小: {len(content)} bytes")
            return content

        except Exception as e:
            logger.error(f"[LocalStorage] 文件下载失败: {key}, {e}")
            raise

    async def download_to_file(self, key: str, local_path: str) -> None:
        """
        下载文件到本地

        Args:
            key: 源文件路径
            local_path: 目标文件路径
        """
        content = await self.download(key)
        dest = Path(local_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(dest.write_bytes, content)
        logger.info(f"[LocalStorage] 文件下载到: {local_path}")

    async def delete(self, key: str) -> bool:
        """
        删除文件

        Args:
            key: 文件路径

        Returns:
            bool: 是否删除成功
        """
        self._ensure_connected()

        file_path = self._get_file_path(key)

        try:
            if file_path.exists():
                await asyncio.to_thread(file_path.unlink)
                logger.info(f"[LocalStorage] 文件删除成功: {key}")
            else:
                logger.warning(f"[LocalStorage] 文件不存在: {key}")

            # 清理空目录
            await self._cleanup_empty_dirs(file_path.parent)

            return True

        except Exception as e:
            logger.error(f"[LocalStorage] 文件删除失败: {key}, {e}")
            return False

    async def _cleanup_empty_dirs(self, directory: Path) -> None:
        """
        递归清理空目录

        Args:
            directory: 要检查的目录
        """
        try:
            # 不删除根目录
            if directory == self.base_path or not directory.is_relative_to(self.base_path):
                return

            # 如果目录为空，删除它
            if directory.exists() and not any(directory.iterdir()):
                await asyncio.to_thread(directory.rmdir)
                logger.debug(f"[LocalStorage] 删除空目录: {directory.relative_to(self.base_path)}")

                # 递归检查父目录
                await self._cleanup_empty_dirs(directory.parent)

        except Exception as e:
            logger.debug(f"[LocalStorage] 清理目录失败: {e}")

    async def exists(self, key: str) -> bool:
        """
        检查文件是否存在

        Args:
            key: 文件路径

        Returns:
            bool: 文件是否存在
        """
        self._ensure_connected()

        file_path = self._get_file_path(key)
        return await asyncio.to_thread(file_path.exists)

    def get_signed_url(
        self,
        key: str,
        expires: int = 3600,
        method: str = "GET"
    ) -> str:
        """
        生成临时访问 URL

        注意：本地存储的临时 URL 是通过 API 端点提供的，格式为：
        /api/storage/download/{key}?token={token}

        Args:
            key: 文件路径
            expires: 有效期（秒）
            method: HTTP 方法

        Returns:
            str: 临时 URL
        """
        self._ensure_connected()

        # 生成临时 token
        token_data = f"{key}:{expires}:{datetime.now().timestamp()}"
        token = hashlib.sha256(token_data.encode()).hexdigest()[:16]

        # 保存 token（生产环境应该用 Redis）
        self._temp_tokens[token] = {
            "key": key,
            "expires_at": datetime.now() + timedelta(seconds=expires),
            "method": method,
        }

        # 构建 URL
        safe_key = quote(key, safe="")
        url = f"/api/storage/download/{safe_key}?token={token}"

        logger.debug(f"[LocalStorage] 生成临时 URL: {key}, 有效期: {expires}秒")
        return url

    def get_url(self, key: str) -> str:
        """
        获取文件的本地路径 URL

        Args:
            key: 文件路径

        Returns:
            str: 本地文件 URL
        """
        return f"local://{key}"

    def verify_token(self, token: str) -> Optional[str]:
        """
        验证临时访问 token

        Args:
            token: 访问 token

        Returns:
            Optional[str]: 文件路径，token 无效返回 None
        """
        token_info = self._temp_tokens.get(token)

        if not token_info:
            return None

        # 检查是否过期
        if datetime.now() > token_info["expires_at"]:
            del self._temp_tokens[token]
            return None

        return token_info["key"]

    async def get_object_meta(self, key: str) -> Optional[dict]:
        """
        获取文件元信息

        Args:
            key: 文件路径

        Returns:
            dict: 文件元信息
        """
        self._ensure_connected()

        file_path = self._get_file_path(key)

        if not file_path.exists():
            return None

        try:
            stat = await asyncio.to_thread(file_path.stat)
            content_type, _ = mimetypes.guess_type(str(file_path))

            return {
                "size": stat.st_size,
                "content_type": content_type or "application/octet-stream",
                "last_modified": datetime.fromtimestamp(stat.st_mtime),
                "etag": None,
            }

        except Exception as e:
            logger.error(f"[LocalStorage] 获取元信息失败: {key}, {e}")
            return None

    async def list_objects(
        self,
        prefix: str = "",
        max_keys: int = 100
    ) -> list[dict]:
        """
        列出文件

        Args:
            prefix: 路径前缀
            max_keys: 最大数量

        Returns:
            list[dict]: 文件列表
        """
        self._ensure_connected()

        prefix_path = self._get_file_path(prefix)

        if not prefix_path.exists():
            return []

        files = []

        try:
            # 递归遍历目录
            for file_path in prefix_path.rglob("*"):
                if file_path.is_file():
                    stat = await asyncio.to_thread(file_path.stat)
                    relative_key = file_path.relative_to(self.base_path)

                    files.append({
                        "key": str(relative_key),
                        "size": stat.st_size,
                        "last_modified": datetime.fromtimestamp(stat.st_mtime),
                    })

                    if len(files) >= max_keys:
                        break

            return files

        except Exception as e:
            logger.error(f"[LocalStorage] 列出文件失败: {prefix}, {e}")
            return []


# ==================== 全局单例 ====================

local_storage = LocalFileStorage()


# ==================== 依赖注入 ====================

def get_local_storage() -> LocalFileStorage:
    """
    获取本地存储实例（依赖注入用）

    Returns:
        LocalFileStorage: 本地存储实例
    """
    if not local_storage._initialized:
        local_storage.connect()
    return local_storage
