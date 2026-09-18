"""公厕改造项目相关数据结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import MilestoneConclusion, RenovationStatus
from app.schemas.restroom import RestroomBrief


class RenovationMilestoneCreate(BaseModel):
    """按节点上报进度与阶段验收结论。"""

    node: str = Field(min_length=1, max_length=60, description="节点名称")
    progress: int = Field(ge=0, le=100, description="节点进度（百分比）")
    conclusion: MilestoneConclusion = Field(
        default=MilestoneConclusion.PASSED, description="阶段验收结论"
    )
    operator: str = Field(min_length=1, max_length=60, description="记录人")
    note: str | None = Field(default=None, max_length=500, description="说明")


class RenovationMilestoneOut(BaseModel):
    """项目档案流水节点。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    node: str
    progress: int | None = None
    conclusion: str = ""
    operator: str
    note: str | None = None
    created_at: datetime


class RenovationCreate(BaseModel):
    """立项登记：改造事由、立项时间、施工单位、计划工期与预算。"""

    restroom_id: int = Field(description="所属公厕")
    title: str = Field(min_length=1, max_length=120, description="项目名称")
    reason: str = Field(min_length=1, max_length=500, description="改造事由")
    approved_at: datetime | None = Field(default=None, description="立项时间，留空取当前时间")
    contractor: str = Field(min_length=1, max_length=120, description="施工单位")
    planned_start: datetime = Field(description="计划开工时间")
    planned_end: datetime = Field(description="计划完工时间")
    budget: float = Field(ge=0, description="预算（万元）")
    remark: str | None = Field(default=None, max_length=500, description="备注")

    @model_validator(mode="after")
    def check_schedule(self) -> "RenovationCreate":
        if self.planned_end <= self.planned_start:
            raise ValueError("计划完工时间必须晚于计划开工时间")
        return self


class RenovationUpdate(BaseModel):
    """局部更新项目信息（完工或取消后不可再修改）。"""

    title: str | None = Field(default=None, min_length=1, max_length=120)
    reason: str | None = Field(default=None, min_length=1, max_length=500)
    contractor: str | None = Field(default=None, min_length=1, max_length=120)
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    budget: float | None = Field(default=None, ge=0)
    remark: str | None = Field(default=None, max_length=500)


class RenovationStatusUpdate(BaseModel):
    """一次项目流转操作（开工 / 申请完工验收 / 完工验收 / 取消）。"""

    to_status: RenovationStatus = Field(description="目标状态")
    operator: str = Field(min_length=1, max_length=60, description="操作人")
    conclusion: MilestoneConclusion | None = Field(
        default=None, description="完工验收结论，仅完工验收时填写"
    )
    remark: str | None = Field(default=None, max_length=500, description="处理说明")


class RenovationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    restroom_id: int
    restroom: RestroomBrief | None = None
    title: str
    reason: str
    approved_at: datetime
    contractor: str
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    budget: float
    status: str
    progress: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    completion_conclusion: str = ""
    remark: str | None = None
    schedule_overdue: bool = Field(default=False, description="计划完工时间已过仍未完工")
    created_at: datetime
    updated_at: datetime
    milestones: list[RenovationMilestoneOut] = Field(default_factory=list)
