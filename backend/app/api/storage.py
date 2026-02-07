# app/api/storage.py
# 文件下载 API
#
# 功能说明：
# 1. 提供本地存储文件的 HTTP 下载端点
# 2. 通过 token 验证临时访问权限
# 3. 配合 LocalFileStorage.get_signed_url() 使用

import mimetypes

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.logging import get_logger
from app.storage.local_file import local_storage

logger = get_logger(__name__)

router = APIRouter(prefix="/api/storage", tags=["文件存储"])


@router.get("/download/{key:path}")
async def download_file(
    key: str,
    token: str = Query(..., description="临时访问 token"),
):
    """
    通过临时 token 下载本地存储的文件

    LocalFileStorage.get_signed_url() 生成的 URL 会指向此端点。
    """
    verified_key = local_storage.verify_token(token)
    if not verified_key:
        raise HTTPException(status_code=403, detail="无效或过期的访问链接")

    file_path = local_storage._get_file_path(verified_key)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    content_type, _ = mimetypes.guess_type(str(file_path))

    return FileResponse(
        path=str(file_path),
        media_type=content_type or "application/octet-stream",
        filename=file_path.name,
    )
