"""接口级测试：覆盖台账、巡查、问题整改与统计看板。"""

from datetime import datetime, timedelta

from tests.conftest import full_items


def test_health_and_dictionaries(client):
    assert client.get("/health").json()["status"] == "ok"
    payload = client.get("/api/v1/meta/dictionaries").json()
    assert "待整改" in payload["issue_status"]
    assert len(payload["inspection_check_items"]) == 8
    assert payload["issue_transitions"]["待整改"] == ["整改中", "已关闭"]
    assert "改造中" in payload["renovation_status"]
    assert "拆除清运" in payload["renovation_node_names"]
    assert payload["milestone_conclusion"] == ["通过", "整改后通过", "未通过"]
    assert payload["renovation_transitions"]["已立项"] == ["改造中", "已取消"]


def test_restroom_crud_and_delete_guard(client, restroom):
    assert restroom["code"].startswith("WC-")

    listed = client.get("/api/v1/restrooms", params={"district": "测试区"}).json()
    assert listed["meta"]["total"] >= 1

    detail = client.get(f"/api/v1/restrooms/{restroom['id']}").json()
    assert detail["inspection_count"] == 0
    assert detail["open_issue_count"] == 0

    updated = client.patch(
        f"/api/v1/restrooms/{restroom['id']}", json={"status": "维修中", "manager": "新责任人"}
    ).json()
    assert updated["status"] == "维修中"
    assert updated["manager"] == "新责任人"

    # 存在关联数据时不允许直接删除
    client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "测试巡查员",
            "shift": "早班",
            "items": full_items(9),
        },
    )
    blocked = client.delete(f"/api/v1/restrooms/{restroom['id']}")
    assert blocked.status_code == 409

    ok = client.delete(f"/api/v1/restrooms/{restroom['id']}", params={"force": "true"})
    assert ok.status_code == 200
    assert client.get(f"/api/v1/restrooms/{restroom['id']}").status_code == 404


def test_inspection_scoring_and_filter(client, restroom):
    good = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "李巡查",
            "shift": "中班",
            "items": full_items(9),
            "remark": "整体良好",
        },
    ).json()
    assert good["score"] == 90.0
    assert good["grade"] == "优秀"
    assert good["result"] == "正常"

    bad_items = full_items(9)
    bad_items[0]["score"] = 3
    bad_items[0]["remark"] = "地面污渍"
    bad = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "李巡查",
            "shift": "晚班",
            "items": bad_items,
        },
    ).json()
    assert bad["result"] == "发现问题"
    assert bad["score"] < 90

    filtered = client.get(
        "/api/v1/inspections", params={"result": "发现问题", "restroom_id": restroom["id"]}
    ).json()
    assert filtered["meta"]["total"] == 1
    assert filtered["items"][0]["id"] == bad["id"]
    assert filtered["items"][0]["restroom"]["name"] == restroom["name"]

    today = datetime.now().date().isoformat()
    ranged = client.get(
        "/api/v1/inspections", params={"date_from": today, "date_to": today}
    ).json()
    assert ranged["meta"]["total"] == 2

    duplicate = full_items(5) + [{"name": "地面与台阶清洁", "score": 4}]
    rejected = client.post(
        "/api/v1/inspections",
        json={"restroom_id": restroom["id"], "inspector": "李巡查", "items": duplicate},
    )
    assert rejected.status_code == 400

    empty = client.post(
        "/api/v1/inspections",
        json={"restroom_id": restroom["id"], "inspector": "李巡查", "items": []},
    )
    assert empty.status_code == 422


def test_issue_lifecycle(client, restroom):
    inspection = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "王巡查",
            "items": full_items(4),
        },
    ).json()

    issue = client.post(
        "/api/v1/issues",
        json={
            "restroom_id": restroom["id"],
            "inspection_id": inspection["id"],
            "title": "地面污渍未清理",
            "description": "巡查发现地面有明显污渍",
            "category": "保洁不到位",
            "severity": "严重",
            "reporter": "王巡查",
            "assignee": "保洁班组",
            "deadline": (datetime.now() - timedelta(days=1)).isoformat(),
        },
    ).json()
    assert issue["status"] == "待整改"
    assert len(issue["records"]) == 1
    assert issue["records"][0]["action"] == "上报问题"

    # 越级流转被拒绝：待整改 -> 已完成
    invalid = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "已完成", "operator": "值班长"},
    )
    assert invalid.status_code == 400
    assert "不允许流转" in invalid.json()["detail"]

    options = client.get(f"/api/v1/issues/{issue['id']}/transitions").json()
    assert {option["status"] for option in options} == {"整改中", "已关闭"}

    processing = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "整改中", "operator": "保洁班组张伟", "remark": "已安排清洗"},
    ).json()
    assert processing["status"] == "整改中"
    assert processing["assignee"] == "保洁班组"

    reviewing = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "待验收", "operator": "保洁班组张伟", "remark": "整改完成待验收"},
    ).json()
    assert reviewing["status"] == "待验收"

    # 验收驳回回到整改中
    rejected = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "整改中", "operator": "王巡查", "remark": "角落仍有残留"},
    ).json()
    assert rejected["status"] == "整改中"
    assert rejected["records"][-1]["action"] == "验收驳回"

    for target in ("待验收", "已完成", "已关闭"):
        payload = {"to_status": target, "operator": "值班长", "remark": f"流转到{target}"}
        response = client.post(f"/api/v1/issues/{issue['id']}/transitions", json=payload)
        assert response.status_code == 200, response.text
    final = response.json()
    assert final["status"] == "已关闭"
    assert final["closed_at"] is not None
    assert [record["to_status"] for record in final["records"]][-1] == "已关闭"

    closed_record = client.post(
        f"/api/v1/issues/{issue['id']}/records",
        json={"action": "整改进度", "operator": "值班长", "remark": "补充说明"},
    )
    assert closed_record.status_code == 400

    overdue = client.get("/api/v1/issues", params={"overdue": "true"}).json()
    assert overdue["meta"]["total"] == 0

    # 巡查记录可反查关联问题数量
    detail = client.get(f"/api/v1/inspections/{inspection['id']}").json()
    assert detail["issue_count"] == 1


def test_issue_requires_matching_restroom(client, restroom):
    other = client.post(
        "/api/v1/restrooms",
        json={"name": "另一座公厕", "district": "测试区", "address": "测试路 2 号"},
    ).json()
    inspection = client.post(
        "/api/v1/inspections",
        json={"restroom_id": other["id"], "inspector": "周巡查", "items": full_items(9)},
    ).json()
    mismatch = client.post(
        "/api/v1/issues",
        json={
            "restroom_id": restroom["id"],
            "inspection_id": inspection["id"],
            "title": "关联错误",
        },
    )
    assert mismatch.status_code == 400
    assert "不一致" in mismatch.json()["detail"]


def test_dashboard_stats(client, restroom):
    payload = client.get("/api/v1/stats/dashboard", params={"trend_days": 7}).json()
    overview = payload["overview"]
    assert overview["restroom_total"] >= 1
    assert overview["inspection_total"] >= 1
    assert len(payload["inspection_trend"]) == 7
    assert {item["name"] for item in payload["issue_by_status"]} == {
        "待整改",
        "整改中",
        "待验收",
        "已完成",
        "已关闭",
    }
    assert payload["top_restrooms"]
    assert "rectification_rate" in overview
    assert "renovation_active" in overview


def _renovation_payload(restroom_id: int, **overrides) -> dict:
    payload = {
        "restroom_id": restroom_id,
        "title": "无障碍设施提升改造",
        "reason": "设施老化，无障碍通道缺失，群众反映强烈",
        "contractor": "市政工程一公司",
        "planned_start": datetime.now().isoformat(),
        "planned_end": (datetime.now() + timedelta(days=30)).isoformat(),
        "budget": 25.6,
    }
    payload.update(overrides)
    return payload


def test_renovation_lifecycle(client, restroom):
    # 立项登记：改造事由、立项时间、施工单位、计划工期与预算
    project = client.post(
        "/api/v1/renovations", json=_renovation_payload(restroom["id"])
    ).json()
    assert project["status"] == "已立项"
    assert project["code"].startswith("GZ-")
    assert project["progress"] == 0
    assert project["milestones"][0]["node"] == "项目立项"

    # 立项阶段公厕状态不变
    detail = client.get(f"/api/v1/restrooms/{restroom['id']}").json()
    assert detail["status"] == "正常开放"

    # 计划完工早于计划开工会被拒绝
    bad_schedule = client.post(
        "/api/v1/renovations",
        json=_renovation_payload(
            restroom["id"],
            planned_start=datetime.now().isoformat(),
            planned_end=(datetime.now() - timedelta(days=1)).isoformat(),
        ),
    )
    assert bad_schedule.status_code == 422

    # 越级流转被拒绝：已立项 -> 已完工
    invalid = client.post(
        f"/api/v1/renovations/{project['id']}/transitions",
        json={"to_status": "已完工", "operator": "验收组"},
    )
    assert invalid.status_code == 400
    assert "不允许流转" in invalid.json()["detail"]

    options = client.get(f"/api/v1/renovations/{project['id']}/transitions").json()
    assert {option["status"] for option in options} == {"改造中", "已取消"}

    # 开工：改造期间公厕自动转为停用
    started = client.post(
        f"/api/v1/renovations/{project['id']}/transitions",
        json={"to_status": "改造中", "operator": "项目部", "remark": "进场施工"},
    ).json()
    assert started["status"] == "改造中"
    assert started["started_at"] is not None
    detail = client.get(f"/api/v1/restrooms/{restroom['id']}").json()
    assert detail["status"] == "暂停使用"

    # 同一公厕不允许重复立项
    duplicate = client.post("/api/v1/renovations", json=_renovation_payload(restroom["id"]))
    assert duplicate.status_code == 409

    # 按节点记录进度与阶段验收结论
    first = client.post(
        f"/api/v1/renovations/{project['id']}/milestones",
        json={
            "node": "拆除清运",
            "progress": 30,
            "conclusion": "通过",
            "operator": "监理单位",
            "note": "旧洁具拆除完毕",
        },
    ).json()
    assert first["progress"] == 30
    second = client.post(
        f"/api/v1/renovations/{project['id']}/milestones",
        json={"node": "土建施工", "progress": 60, "conclusion": "整改后通过", "operator": "监理单位"},
    ).json()
    assert second["progress"] == 60
    node_records = [m for m in second["milestones"] if m["kind"] == "节点进度"]
    assert [m["node"] for m in node_records] == ["拆除清运", "土建施工"]
    assert node_records[1]["conclusion"] == "整改后通过"

    # 申请完工验收 -> 验收退回 -> 再次申请 -> 完工验收通过
    client.post(
        f"/api/v1/renovations/{project['id']}/transitions",
        json={"to_status": "待完工验收", "operator": "施工单位"},
    )
    returned = client.post(
        f"/api/v1/renovations/{project['id']}/transitions",
        json={"to_status": "改造中", "operator": "验收组", "remark": "两处细节需整改"},
    ).json()
    assert returned["status"] == "改造中"
    # 退回整改期间公厕仍处于停用状态
    detail = client.get(f"/api/v1/restrooms/{restroom['id']}").json()
    assert detail["status"] == "暂停使用"

    client.post(
        f"/api/v1/renovations/{project['id']}/transitions",
        json={"to_status": "待完工验收", "operator": "施工单位"},
    )
    done = client.post(
        f"/api/v1/renovations/{project['id']}/transitions",
        json={
            "to_status": "已完工",
            "operator": "验收组",
            "conclusion": "通过",
            "remark": "现场验收合格",
        },
    ).json()
    assert done["status"] == "已完工"
    assert done["progress"] == 100
    assert done["completion_conclusion"] == "通过"
    assert done["finished_at"] is not None

    # 完工验收后公厕恢复开放
    detail = client.get(f"/api/v1/restrooms/{restroom['id']}").json()
    assert detail["status"] == "正常开放"

    # 已完工项目归档：不允许再修改、再记节点
    blocked_edit = client.patch(
        f"/api/v1/renovations/{project['id']}", json={"budget": 30}
    )
    assert blocked_edit.status_code == 400
    blocked_node = client.post(
        f"/api/v1/renovations/{project['id']}/milestones",
        json={"node": "其他", "progress": 100, "operator": "监理单位"},
    )
    assert blocked_node.status_code == 400

    # 整份项目档案保留：立项、开工、节点、验收记录完整可查
    archive = client.get(f"/api/v1/renovations/{project['id']}").json()
    flow_nodes = [m["node"] for m in archive["milestones"] if m["kind"] == "流程事件"]
    assert flow_nodes == ["项目立项", "开工", "申请完工验收", "验收退回整改", "申请完工验收", "完工验收通过"]
    completion = archive["milestones"][-1]
    assert completion["conclusion"] == "通过"
    assert completion["operator"] == "验收组"


def test_renovation_cancel_restores_restroom(client, restroom):
    project = client.post(
        "/api/v1/renovations", json=_renovation_payload(restroom["id"])
    ).json()
    client.post(
        f"/api/v1/renovations/{project['id']}/transitions",
        json={"to_status": "改造中", "operator": "项目部"},
    )
    assert client.get(f"/api/v1/restrooms/{restroom['id']}").json()["status"] == "暂停使用"

    cancelled = client.post(
        f"/api/v1/renovations/{project['id']}/transitions",
        json={"to_status": "已取消", "operator": "项目管理办公室", "remark": "资金未落实，暂缓实施"},
    ).json()
    assert cancelled["status"] == "已取消"
    # 取消后公厕恢复为改造前状态
    assert client.get(f"/api/v1/restrooms/{restroom['id']}").json()["status"] == "正常开放"
    # 取消后可重新立项
    again = client.post("/api/v1/renovations", json=_renovation_payload(restroom["id"]))
    assert again.status_code == 201


def test_renovation_list_filters(client, restroom):
    client.post("/api/v1/renovations", json=_renovation_payload(restroom["id"]))
    listed = client.get(
        "/api/v1/renovations", params={"restroom_id": restroom["id"], "status": "已立项"}
    ).json()
    assert listed["meta"]["total"] == 1
    assert listed["items"][0]["restroom"]["name"] == restroom["name"]

    by_keyword = client.get("/api/v1/renovations", params={"keyword": "无障碍"}).json()
    assert by_keyword["meta"]["total"] >= 1

    by_district = client.get("/api/v1/renovations", params={"district": "测试区"}).json()
    assert by_district["meta"]["total"] >= 1
