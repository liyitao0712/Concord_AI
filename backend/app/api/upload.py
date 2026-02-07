# app/api/upload.py
# 通用文件上传 API
#
# 功能说明：
# 1. 接受 multipart/form-data 文件上传
# 2. 自动选择 OSS 或本地存储（OSS 优先，本地降级）
# 3. 返回存储 key 和 storage_type
#
# 路由：
#   POST /admin/upload  通用文件上传

import mimetypes
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.security import get_current_admin_user
from app.models.user import User
from app.storage.oss import oss_client
from app.storage.local_file import local_storage

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/upload", tags=["文件上传"])

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


class UploadResponse(BaseModel):
    """上传响应"""
    key: str
    storage_type: str  # "oss" 或 "local"
    url: str  # 可直接访问的 URL


@router.post("", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    directory: str = Form("images/general", description="存储目录，如 images/categories"),
    admin: User = Depends(get_current_admin_user),
):
    """
    通用文件上传

    上传图片文件，自动选择 OSS 或本地存储。
    返回存储 key 和可访问的 URL。
    """
    # 验证文件类型
    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {content_type}，仅支持 JPEG/PNG/GIF/WebP")

    # 读取文件内容
    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制（最大 {MAX_IMAGE_SIZE // 1024 // 1024}MB）")

    # 生成存储 key
    ext = mimetypes.guess_extension(content_type) or ".bin"
    # mimetypes 对 jpeg 返回 .jpeg，统一为 .jpg
    if ext == ".jpeg":
        ext = ".jpg"
    safe_directory = directory.strip("/").replace("..", "")
    key = f"{safe_directory}/{uuid4().hex}{ext}"

    # 上传：OSS 优先，本地降级
    storage_type = "oss"
    try:
        oss_client.connect()
        await oss_client.upload(key=key, data=data, content_type=content_type)
    except Exception as e:
        logger.warning(f"[Upload] OSS 上传失败，降级到本地存储: {e}")
        storage_type = "local"
        try:
            local_storage.connect()
            await local_storage.upload(key=key, data=data, content_type=content_type)
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"文件上传失败: {e2}")

    # 生成访问 URL
    if storage_type == "oss":
        url = oss_client.get_signed_url(key, expires=3600)
    else:
        url = local_storage.get_signed_url(key, expires=3600)

    logger.info(f"[Upload] 文件上传成功: {key} ({storage_type}) by {admin.email}")
    return UploadResponse(key=key, storage_type=storage_type, url=url)
