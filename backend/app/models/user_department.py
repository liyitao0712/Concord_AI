# app/models/user_department.py
# 用户-部门关联模型（多对多）

from uuid import uuid4

from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserDepartment(Base):
    """
    用户-部门关联（多对多）

    支持一个用户关联多个部门（如副总同时管理销售部和采购部）。
    is_primary 标记主部门，新建数据时默认归属到主部门。
    """

    __tablename__ = "user_departments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    department_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否主部门"
    )

    # 关系
    user = relationship("User", back_populates="user_departments")
    department = relationship("Department")

    def __repr__(self) -> str:
        return f"<UserDepartment(user_id={self.user_id}, dept_id={self.department_id}, primary={self.is_primary})>"
