"""业务枚举与规则常量。"""

from enum import StrEnum


class RestroomStatus(StrEnum):
    NORMAL = "正常开放"
    MAINTENANCE = "维修中"
    CLOSED = "暂停使用"


class RestroomGrade(StrEnum):
    FIRST = "一类"
    SECOND = "二类"
    THIRD = "三类"


class Shift(StrEnum):
    MORNING = "早班"
    MIDDLE = "中班"
    NIGHT = "晚班"


class InspectionResult(StrEnum):
    NORMAL = "正常"
    ABNORMAL = "发现问题"


class IssueCategory(StrEnum):
    CLEANING = "保洁不到位"
    FACILITY = "设施损坏"
    ODOR = "异味扰民"
    CONSUMABLE = "耗材缺失"
    SAFETY = "安全隐患"
    OTHER = "其他"


class IssueSeverity(StrEnum):
    NORMAL = "一般"
    SERIOUS = "严重"
    URGENT = "紧急"


class IssueStatus(StrEnum):
    PENDING = "待整改"
    PROCESSING = "整改中"
    REVIEWING = "待验收"
    DONE = "已完成"
    CLOSED = "已关闭"
# 整改流转规则：当前状态 -> 允许流转到的状态
ISSUE_TRANSITIONS: dict[str, list[str]] = {
    IssueStatus.PENDING: [IssueStatus.PROCESSING, IssueStatus.CLOSED],
    IssueStatus.PROCESSING: [IssueStatus.REVIEWING, IssueStatus.CLOSED],
    IssueStatus.REVIEWING: [IssueStatus.DONE, IssueStatus.PROCESSING],
    IssueStatus.DONE: [IssueStatus.CLOSED],
    IssueStatus.CLOSED: [],
}

# 状态流转对应的动作名称，用于生成整改流水
TRANSITION_ACTIONS: dict[tuple[str, str], str] = {
    (IssueStatus.PENDING, IssueStatus.PROCESSING): "开始整改",
    (IssueStatus.PENDING, IssueStatus.CLOSED): "作废关闭",
    (IssueStatus.PROCESSING, IssueStatus.REVIEWING): "提交验收",
    (IssueStatus.PROCESSING, IssueStatus.CLOSED): "终止关闭",
    (IssueStatus.REVIEWING, IssueStatus.DONE): "验收通过",
    (IssueStatus.REVIEWING, IssueStatus.PROCESSING): "验收驳回",
    (IssueStatus.DONE, IssueStatus.CLOSED): "归档关闭",
}

# 巡查检查项，每项 0-10 分
INSPECTION_CHECK_ITEMS: list[str] = [
    "地面与台阶清洁",
    "便池蹲位清洁",
    "洗手台与镜面",
    "通风除臭",
    "耗材补充",
    "垃圾清运",
    "工具与标识摆放",
    "墙面门窗卫生",
]

INSPECTION_ITEM_MAX_SCORE = 10

GRADE_EXCELLENT = "优秀"
GRADE_GOOD = "良好"
GRADE_PASS = "合格"
GRADE_FAIL = "不合格"

# 仍处于整改闭环中的状态，用于统计未整改问题
OPEN_ISSUE_STATUSES: list[str] = [
    IssueStatus.PENDING,
    IssueStatus.PROCESSING,
    IssueStatus.REVIEWING,
]

# 单检查项低于该分数视为不合格项
INSPECTION_ITEM_PROBLEM_THRESHOLD = 6


class RenovationStatus(StrEnum):
    """改造项目状态。"""

    APPROVED = "已立项"
    WORKING = "改造中"
    ACCEPTANCE = "待完工验收"
    COMPLETED = "已完工"
    CANCELLED = "已取消"


class MilestoneConclusion(StrEnum):
    """节点/完工验收结论。"""

    PASSED = "通过"
    CONDITIONAL = "整改后通过"
    FAILED = "未通过"


# 改造项目流转规则：当前状态 -> 允许流转到的状态
RENOVATION_TRANSITIONS: dict[str, list[str]] = {
    RenovationStatus.APPROVED: [RenovationStatus.WORKING, RenovationStatus.CANCELLED],
    RenovationStatus.WORKING: [RenovationStatus.ACCEPTANCE, RenovationStatus.CANCELLED],
    RenovationStatus.ACCEPTANCE: [RenovationStatus.COMPLETED, RenovationStatus.WORKING],
    RenovationStatus.COMPLETED: [],
    RenovationStatus.CANCELLED: [],
}

# 项目流转对应的动作名称，用于生成项目档案流水
RENOVATION_TRANSITION_ACTIONS: dict[tuple[str, str], str] = {
    (RenovationStatus.APPROVED, RenovationStatus.WORKING): "开工",
    (RenovationStatus.APPROVED, RenovationStatus.CANCELLED): "取消项目",
    (RenovationStatus.WORKING, RenovationStatus.ACCEPTANCE): "申请完工验收",
    (RenovationStatus.WORKING, RenovationStatus.CANCELLED): "中止取消",
    (RenovationStatus.ACCEPTANCE, RenovationStatus.COMPLETED): "完工验收通过",
    (RenovationStatus.ACCEPTANCE, RenovationStatus.WORKING): "验收退回整改",
}

# 仍处于改造周期内、占用公厕的项目状态（同一公厕同一时间只允许一个，
# 也用于工期超期预警：这些状态下计划完工日期已过即视为超期）
ACTIVE_RENOVATION_STATUSES: list[str] = [
    RenovationStatus.APPROVED,
    RenovationStatus.WORKING,
    RenovationStatus.ACCEPTANCE,
]

# 常用的改造节点名称，供前端下拉选择
RENOVATION_NODE_NAMES: list[str] = [
    "拆除清运",
    "土建施工",
    "水电改造",
    "防水工程",
    "装饰装修",
    "设备安装",
    "环境恢复",
    "其他",
]
