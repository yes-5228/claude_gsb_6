"""公厕改造项目模型。"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import RenovationStatus
from app.core.database import Base


class RenovationProject(Base):
    """公厕改造项目：登记立项信息，跟踪进度直至完工验收归档。"""

    __tablename__ = "renovation_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="项目编号")
    restroom_id: Mapped[int] = mapped_column(
        ForeignKey("restrooms.id", ondelete="CASCADE"), index=True, comment="所属公厕"
    )
    title: Mapped[str] = mapped_column(String(120), comment="项目名称")
    reason: Mapped[str] = mapped_column(Text, default="", comment="改造事由")
    approved_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="立项时间"
    )
    contractor: Mapped[str] = mapped_column(String(120), default="", comment="施工单位")
    planned_start: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="计划开工时间"
    )
    planned_end: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="计划完工时间"
    )
    budget: Mapped[float] = mapped_column(Float, default=0.0, comment="预算（万元）")
    status: Mapped[str] = mapped_column(
        String(20), default=RenovationStatus.APPROVED.value, index=True, comment="项目状态"
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, comment="整体进度（百分比）")
    previous_restroom_status: Mapped[str] = mapped_column(
        String(20), default="", comment="改造前公厕开放状态，完工验收后恢复"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="实际开工时间"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="完工验收时间"
    )
    completion_conclusion: Mapped[str] = mapped_column(
        String(20), default="", comment="完工验收结论"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    restroom: Mapped["Restroom"] = relationship(back_populates="renovations")  # noqa: F821
    milestones: Mapped[list["RenovationMilestone"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="RenovationMilestone.created_at, RenovationMilestone.id",
    )


class RenovationMilestone(Base):
    """改造项目档案流水：节点进度（含阶段验收结论）与流程事件统一归档。"""

    __tablename__ = "renovation_milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("renovation_projects.id", ondelete="CASCADE"), index=True, comment="所属项目"
    )
    kind: Mapped[str] = mapped_column(String(10), default="节点进度", comment="记录类型")
    node: Mapped[str] = mapped_column(String(60), comment="节点名称或流程动作")
    progress: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="节点进度（百分比）"
    )
    conclusion: Mapped[str] = mapped_column(String(20), default="", comment="阶段验收结论")
    operator: Mapped[str] = mapped_column(String(60), default="", comment="记录人")
    note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="说明")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="记录时间"
    )

    project: Mapped["RenovationProject"] = relationship(back_populates="milestones")
