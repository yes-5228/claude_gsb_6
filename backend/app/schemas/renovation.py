"""公厕改造项目跟踪相关数据结构。"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.core.constants import NodeAcceptance, RenovationStatus
from app.schemas.restroom import RestroomBrief


class RenovationNodeOut(BaseModel):
    """进度节点（含阶段验收结论）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    node_date: date
    progress: str = ""
    progress_percent: int | None = None
    operator: str = ""
    acceptance_result: str = ""
    acceptance_opinion: str | None = None
    acceptor: str = ""
    accepted_at: datetime | None = None
    created_at: datetime


class RenovationRecordOut(BaseModel):
    """项目流转流水节点。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    from_status: str
    to_status: str
    operator: str
    remark: str | None = None
    created_at: datetime


class RenovationProjectCreate(BaseModel):
    restroom_id: int
    reason: str = Field(min_length=1, max_length=1000, description="改造事由")
    construction_unit: str = Field(default="", max_length=120, description="施工单位")
    project_manager: str = Field(default="", max_length=60, description="现场负责人")
    contact_phone: str = Field(default="", max_length=30, description="联系电话")
    setup_time: datetime | None = Field(default=None, description="立项时间，留空取当前时间")
    planned_start_date: date | None = Field(default=None, description="计划开工日期")
    planned_end_date: date | None = Field(default=None, description="计划完工日期")
    budget: float = Field(default=0, ge=0, description="预算金额（万元）")
    remark: str | None = Field(default=None, max_length=500, description="备注")

    @model_validator(mode="after")
    def _check_dates(self) -> "RenovationProjectCreate":
        if (
            self.planned_start_date is not None
            and self.planned_end_date is not None
            and self.planned_end_date < self.planned_start_date
        ):
            raise ValueError("计划完工日期不能早于计划开工日期")
        return self


class RenovationProjectUpdate(BaseModel):
    """局部更新登记信息（公厕与状态不可在此修改）。"""

    reason: str | None = Field(default=None, min_length=1, max_length=1000)
    construction_unit: str | None = Field(default=None, max_length=120)
    project_manager: str | None = Field(default=None, max_length=60)
    contact_phone: str | None = Field(default=None, max_length=30)
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    budget: float | None = Field(default=None, ge=0)
    actual_cost: float | None = Field(default=None, ge=0)
    remark: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _check_dates(self) -> "RenovationProjectUpdate":
        if (
            self.planned_start_date is not None
            and self.planned_end_date is not None
            and self.planned_end_date < self.planned_start_date
        ):
            raise ValueError("计划完工日期不能早于计划开工日期")
        return self


class RenovationNodeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120, description="节点名称")
    node_date: date = Field(description="节点日期")
    progress: str = Field(default="", max_length=1000, description="进度说明")
    progress_percent: int | None = Field(default=None, ge=0, le=100, description="完成度（0-100）")
    operator: str = Field(default="", max_length=60, description="填报人")


class RenovationNodeAcceptance(BaseModel):
    """节点阶段验收结论登记（可复验覆盖）。"""

    result: NodeAcceptance = Field(description="阶段验收结论")
    opinion: str | None = Field(default=None, max_length=500, description="验收意见")
    acceptor: str = Field(min_length=1, max_length=60, description="验收人")


class RenovationStatusUpdate(BaseModel):
    """一次项目状态流转操作。"""

    to_status: RenovationStatus = Field(description="目标状态")
    operator: str = Field(min_length=1, max_length=60, description="操作人")
    remark: str | None = Field(default=None, max_length=500, description="处理说明")
    actual_cost: float | None = Field(default=None, ge=0, description="结算造价（万元），竣工验收时填写")


class RenovationProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    restroom_id: int
    restroom: RestroomBrief | None = None
    reason: str
    construction_unit: str
    project_manager: str
    contact_phone: str
    status: str
    setup_time: datetime
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    budget: float
    actual_cost: float | None = None
    previous_restroom_status: str = ""
    actual_start_time: datetime | None = None
    accepted_at: datetime | None = None
    accepted_opinion: str | None = None
    remark: str | None = None
    created_at: datetime
    updated_at: datetime
    nodes: list[RenovationNodeOut] = Field(default_factory=list)
    records: list[RenovationRecordOut] = Field(default_factory=list)

    @computed_field
    @property
    def plan_duration_days(self) -> int | None:
        if self.planned_start_date is None or self.planned_end_date is None:
            return None
        return (self.planned_end_date - self.planned_start_date).days + 1

    @computed_field
    @property
    def is_delayed(self) -> bool:
        """超过计划完工日期仍未竣工验收。"""
        return (
            self.status != RenovationStatus.ACCEPTED.value
            and self.planned_end_date is not None
            and self.planned_end_date < date.today()
        )
