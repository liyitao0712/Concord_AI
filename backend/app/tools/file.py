# app/tools/file.py
# 文件操作工具
#
# 提供 Agent 操作文件的能力：
# - 读取文件内容
# - 写入文件
# - 列出文件
# - 删除文件
#
# 注意：当前版本使用本地临时目录
# 后续可接入阿里云 OSS 实现云存储

import os
import json
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.tools.base import BaseTool, tool
from app.tools.registry import register_tool

logger = get_logger(__name__)

# 工作目录（使用临时目录或配置的目录）
WORK_DIR = Path(tempfile.gettempdir()) / "concord_files"
WORK_DIR.mkdir(parents=True, exist_ok=True)


@register_tool
class FileTool(BaseTool):
    """
    文件操作工具

    提供 Agent 操作文件的能力
    当前使用本地临时目录，后续可接入 OSS
    """

    name = "file"
    description = "读取、写入和管理文件"

    @tool(
        name="read_file",
        description="读取文件内容",
        parameters={
            "path": {
                "type": "string",
                "description": "文件路径（相对于工作目录）",
            },
            "encoding": {
                "type": "string",
                "description": "文件编码（默认 utf-8）",
            },
        },
    )
    async def read_file(
        self,
        path: str,
        encoding: str = "utf-8",
    ) -> dict:
        """读取文件内容"""
        logger.info(f"[FileTool] 读取文件: {path}")

        try:
            # 安全检查：防止路径穿越
            file_path = self._safe_path(path)
            if file_path is None:
                return {
                    "success": False,
                    "error": "无效的文件路径",
                }

            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"文件不存在: {path}",
                }

            if not file_path.is_file():
                return {
                    "success": False,
                    "error": f"不是文件: {path}",
                }

            # 读取内容
            content = file_path.read_text(encoding=encoding)

            return {
                "success": True,
                "path": path,
                "content": content,
                "size": len(content),
            }

        except UnicodeDecodeError:
            return {
                "success": False,
                "error": f"无法以 {encoding} 编码读取文件",
            }
        except Exception as e:
            logger.error(f"[FileTool] 读取失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @tool(
        name="write_file",
        description="写入文件内容",
        parameters={
            "path": {
                "type": "string",
                "description": "文件路径（相对于工作目录）",
            },
            "content": {
                "type": "string",
                "description": "文件内容",
            },
            "encoding": {
                "type": "string",
                "description": "文件编码（默认 utf-8）",
            },
            "append": {
                "type": "boolean",
                "description": "是否追加模式（默认覆盖）",
            },
        },
    )
    async def write_file(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        append: bool = False,
    ) -> dict:
        """写入文件内容"""
        logger.info(f"[FileTool] 写入文件: {path}, append={append}")

        try:
            # 安全检查
            file_path = self._safe_path(path)
            if file_path is None:
                return {
                    "success": False,
                    "error": "无效的文件路径",
                }

            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入内容
            mode = "a" if append else "w"
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)

            return {
                "success": True,
                "path": path,
                "size": len(content),
                "mode": "append" if append else "overwrite",
            }

        except Exception as e:
            logger.error(f"[FileTool] 写入失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @tool(
        name="list_files",
        description="列出目录中的文件",
        parameters={
            "path": {
                "type": "string",
                "description": "目录路径（相对于工作目录，默认根目录）",
            },
            "pattern": {
                "type": "string",
                "description": "文件名匹配模式（如 *.txt）",
            },
            "recursive": {
                "type": "boolean",
                "description": "是否递归列出子目录",
            },
        },
    )
    async def list_files(
        self,
        path: str = "",
        pattern: str = "*",
        recursive: bool = False,
    ) -> dict:
        """列出目录中的文件"""
        logger.info(f"[FileTool] 列出文件: {path}, pattern={pattern}")

        try:
            # 安全检查
            dir_path = self._safe_path(path) if path else WORK_DIR
            if dir_path is None:
                return {
                    "success": False,
                    "error": "无效的目录路径",
                    "files": [],
                }

            if not dir_path.exists():
                return {
                    "success": False,
                    "error": f"目录不存在: {path}",
                    "files": [],
                }

            if not dir_path.is_dir():
                return {
                    "success": False,
                    "error": f"不是目录: {path}",
                    "files": [],
                }

            # 列出文件
            if recursive:
                files = list(dir_path.rglob(pattern))
            else:
                files = list(dir_path.glob(pattern))

            # 构建文件信息
            file_list = []
            for f in files:
                try:
                    stat = f.stat()
                    file_list.append({
                        "name": f.name,
                        "path": str(f.relative_to(WORK_DIR)),
                        "is_dir": f.is_dir(),
                        "size": stat.st_size if f.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
                except Exception:
                    pass

            # 按名称排序
            file_list.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

            return {
                "success": True,
                "path": path or "/",
                "count": len(file_list),
                "files": file_list,
            }

        except Exception as e:
            logger.error(f"[FileTool] 列出失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "files": [],
            }

    @tool(
        name="delete_file",
        description="删除文件",
        parameters={
            "path": {
                "type": "string",
                "description": "文件路径（相对于工作目录）",
            },
        },
    )
    async def delete_file(self, path: str) -> dict:
        """删除文件"""
        logger.info(f"[FileTool] 删除文件: {path}")

        try:
            # 安全检查
            file_path = self._safe_path(path)
            if file_path is None:
                return {
                    "success": False,
                    "error": "无效的文件路径",
                }

            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"文件不存在: {path}",
                }

            if file_path.is_dir():
                return {
                    "success": False,
                    "error": "不能删除目录，请使用 delete_directory",
                }

            # 删除文件
            file_path.unlink()

            return {
                "success": True,
                "path": path,
            }

        except Exception as e:
            logger.error(f"[FileTool] 删除失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @tool(
        name="create_directory",
        description="创建目录",
        parameters={
            "path": {
                "type": "string",
                "description": "目录路径（相对于工作目录）",
            },
        },
    )
    async def create_directory(self, path: str) -> dict:
        """创建目录"""
        logger.info(f"[FileTool] 创建目录: {path}")

        try:
            # 安全检查
            dir_path = self._safe_path(path)
            if dir_path is None:
                return {
                    "success": False,
                    "error": "无效的目录路径",
                }

            # 创建目录
            dir_path.mkdir(parents=True, exist_ok=True)

            return {
                "success": True,
                "path": path,
            }

        except Exception as e:
            logger.error(f"[FileTool] 创建目录失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @tool(
        name="file_exists",
        description="检查文件是否存在",
        parameters={
            "path": {
                "type": "string",
                "description": "文件路径（相对于工作目录）",
            },
        },
    )
    async def file_exists(self, path: str) -> dict:
        """检查文件是否存在"""
        file_path = self._safe_path(path)
        if file_path is None:
            return {
                "exists": False,
                "is_file": False,
                "is_dir": False,
            }

        return {
            "exists": file_path.exists(),
            "is_file": file_path.is_file() if file_path.exists() else False,
            "is_dir": file_path.is_dir() if file_path.exists() else False,
        }

    @tool(
        name="save_json",
        description="保存 JSON 数据到文件",
        parameters={
            "path": {
                "type": "string",
                "description": "文件路径（相对于工作目录）",
            },
            "data": {
                "type": "object",
                "description": "要保存的 JSON 数据",
            },
            "indent": {
                "type": "integer",
                "description": "缩进空格数（默认2）",
            },
        },
    )
    async def save_json(
        self,
        path: str,
        data: dict,
        indent: int = 2,
    ) -> dict:
        """保存 JSON 数据"""
        logger.info(f"[FileTool] 保存 JSON: {path}")

        try:
            content = json.dumps(data, ensure_ascii=False, indent=indent)
            return await self.write_file(path, content)

        except Exception as e:
            logger.error(f"[FileTool] 保存 JSON 失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @tool(
        name="load_json",
        description="从文件加载 JSON 数据",
        parameters={
            "path": {
                "type": "string",
                "description": "文件路径（相对于工作目录）",
            },
        },
    )
    async def load_json(self, path: str) -> dict:
        """加载 JSON 数据"""
        logger.info(f"[FileTool] 加载 JSON: {path}")

        try:
            result = await self.read_file(path)
            if not result["success"]:
                return result

            data = json.loads(result["content"])
            return {
                "success": True,
                "path": path,
                "data": data,
            }

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON 解析失败: {e}",
            }
        except Exception as e:
            logger.error(f"[FileTool] 加载 JSON 失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _safe_path(self, path: str) -> Optional[Path]:
        """
        安全路径检查，防止路径穿越攻击

        Args:
            path: 相对路径

        Returns:
            Path: 安全的绝对路径，如果路径不安全则返回 None
        """
        try:
            # 规范化路径
            clean_path = Path(path).resolve()
            full_path = (WORK_DIR / path).resolve()

            # 检查是否在工作目录内
            if WORK_DIR in full_path.parents or full_path == WORK_DIR:
                return full_path

            # 如果路径尝试逃逸工作目录，返回 None
            if str(full_path).startswith(str(WORK_DIR)):
                return full_path

            return None

        except Exception:
            return None
