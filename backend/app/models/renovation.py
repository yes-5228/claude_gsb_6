"""公厕改造项目跟踪模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import RenovationStatus
from app.core.database import Base


class RenovationProject(Base):
    """公厕改造项目：立项、施工、验收全流程跟踪。"""

    __tablename__ = "renovation_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="项目编号")
    restroom_id: Mapped[int] = mapped_column(
        ForeignKey("restrooms.id", ondelete="CASCADE"), index=True, comment="改造公厕"
    )
    reason: Mapped[str] = mapped_column(Text, comment="改造事由")
    construction_unit: Mapped[str] = mapped_column(String(120), default="", comment="施工单位")
    project_manager: Mapped[str] = mapped_column(String(60), default="", comment="现场负责人")
    contact_phone: Mapped[str] = mapped_column(String(30), default="", comment="联系电话")
    status: Mapped[str] = mapped_column(
        String(20), default=RenovationStatus.PENDING.value, index=True, comment="项目状态"
    )
    setup_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="立项时间"
    )
    planned_start_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="计划开工日期")
    planned_end_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="计划完工日期")
    budget: Mapped[float] = mapped_column(Float, default=0, comment="预算金额（万元）")
    actual_cost: Mapped[float | None] = mapped_column(Float, nullable=True, comment="结算造价（万元）")
    previous_restroom_status: Mapped[str] = mapped_column(
        String(20), default="", comment="立项前公厕状态，验收后据此恢复"
    )
    actual_start_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="实际开工时间"
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="竣工验收时间")
    accepted_opinion: Mapped[str | None] = mapped_column(Text, nullable=True, comment="竣工验收意见")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    restroom: Mapped["Restroom"] = relationship(back_populates="projects")  # noqa: F821
    nodes: Mapped[list["RenovationNode"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="RenovationNode.node_date",
    )
    records: Mapped[list["RenovationRecord"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="RenovationRecord.created_at",
    )


class RenovationNode(Base):
    """改造进度节点，可单独登记阶段验收结论。"""

    __tablename__ = "renovation_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("renovation_projects.id", ondelete="CASCADE"), index=True, comment="所属项目"
    )
    title: Mapped[str] = mapped_column(String(120), comment="节点名称")
    node_date: Mapped[date] = mapped_column(Date, index=True, comment="节点日期")
    progress: Mapped[str] = mapped_column(Text, default="", comment="进度说明")
    progress_percent: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="完成度（0-100）"
    )
    operator: Mapped[str] = mapped_column(String(60), default="", comment="填报人")
    acceptance_result: Mapped[str] = mapped_column(
        String(10), default="", comment="阶段验收结论：合格/不合格，空为未验收"
    )
    acceptance_opinion: Mapped[str | None] = mapped_column(Text, nullable=True, comment="阶段验收意见")
    acceptor: Mapped[str] = mapped_column(String(60), default="", comment="阶段验收人")
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="阶段验收时间"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    project: Mapped["RenovationProject"] = relationship(back_populates="nodes")


class RenovationRecord(Base):
    """项目状态流转流水，用于还原完整的改造过程轨迹。"""

    __tablename__ = "renovation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("renovation_projects.id", ondelete="CASCADE"), index=True, comment="所属项目"
    )
    action: Mapped[str] = mapped_column(String(30), comment="处理动作")
    from_status: Mapped[str] = mapped_column(String(20), default="", comment="原状态")
    to_status: Mapped[str] = mapped_column(String(20), comment="新状态")
    operator: Mapped[str] = mapped_column(String(60), default="", comment="操作人")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处理说明")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="操作时间"
    )

    project: Mapped["RenovationProject"] = relationship(back_populates="records")
