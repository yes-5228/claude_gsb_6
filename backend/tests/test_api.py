"""接口级测试：覆盖台账、巡查、问题整改与统计看板。"""

from datetime import datetime, timedelta

from tests.conftest import full_items


def test_health_and_dictionaries(client):
    assert client.get("/health").json()["status"] == "ok"
    payload = client.get("/api/v1/meta/dictionaries").json()
    assert "待整改" in payload["issue_status"]
    assert len(payload["inspection_check_items"]) == 8
    assert payload["issue_transitions"]["待整改"] == ["整改中", "已关闭"]


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


def _project_payload(restroom_id: int, **overrides) -> dict:
    payload = {
        "restroom_id": restroom_id,
        "reason": "给排水老化渗漏，整体提档改造",
        "construction_unit": "城央建设工程有限公司",
        "project_manager": "林工",
        "contact_phone": "13800000000",
        "planned_start_date": "2026-10-01",
        "planned_end_date": "2026-11-15",
        "budget": 20.5,
    }
    payload.update(overrides)
    return payload


def test_renovation_lifecycle_and_restroom_status(client, restroom):
    # 立项即停用，公厕状态变为暂停使用并记录原状态
    project = client.post("/api/v1/projects", json=_project_payload(restroom["id"])).json()
    assert project["code"].startswith("GZ-")
    assert project["status"] == "待施工"
    assert project["previous_restroom_status"] == "正常开放"
    assert project["plan_duration_days"] == 46
    assert project["records"][0]["action"] == "立项登记"
    assert client.get(f"/api/v1/restrooms/{restroom['id']}").json()["status"] == "暂停使用"

    # 停用期间不能登记巡查
    blocked_inspection = client.post(
        "/api/v1/inspections",
        json={"restroom_id": restroom["id"], "inspector": "测试巡查员", "items": full_items(9)},
    )
    assert blocked_inspection.status_code == 400
    assert "暂停使用" in blocked_inspection.json()["detail"]

    # 同一公厕不能重复立项
    duplicate = client.post("/api/v1/projects", json=_project_payload(restroom["id"]))
    assert duplicate.status_code == 400
    assert "不能重复立项" in duplicate.json()["detail"]

    # 计划完工早于开工返回 422
    bad_dates = client.post(
        "/api/v1/projects",
        json=_project_payload(restroom["id"], planned_end_date="2026-09-01"),
    )
    assert bad_dates.status_code == 422

    # 待施工不能登记进度节点，也不能越级竣工验收
    node_early = client.post(
        f"/api/v1/projects/{project['id']}/nodes",
        json={"title": "拆除", "node_date": "2026-10-02", "operator": "林工"},
    )
    assert node_early.status_code == 400
    jump = client.post(
        f"/api/v1/projects/{project['id']}/transitions",
        json={"to_status": "已验收", "operator": "林工"},
    )
    assert jump.status_code == 400
    assert "不允许流转" in jump.json()["detail"]

    options = client.get(f"/api/v1/projects/{project['id']}/transitions").json()
    assert [item["status"] for item in options] == ["施工中"]

    # 开工：写入实际开工时间
    processing = client.post(
        f"/api/v1/projects/{project['id']}/transitions",
        json={"to_status": "施工中", "operator": "林工", "remark": "进场施工"},
    ).json()
    assert processing["status"] == "施工中"
    assert processing["actual_start_time"] is not None

    # 登记两个节点并做阶段验收（合格、不合格各一次）
    detail = client.post(
        f"/api/v1/projects/{project['id']}/nodes",
        json={
            "title": "水电管线改造",
            "node_date": "2026-10-10",
            "progress": "管线更换完成并试压",
            "progress_percent": 45,
            "operator": "林工",
        },
    ).json()
    node_id = detail["nodes"][0]["id"]
    failed = client.patch(
        f"/api/v1/projects/{project['id']}/nodes/{node_id}",
        json={"result": "不合格", "opinion": "支吊架间距偏大", "acceptor": "监理吴工"},
    ).json()
    assert failed["nodes"][0]["acceptance_result"] == "不合格"
    passed = client.patch(
        f"/api/v1/projects/{project['id']}/nodes/{node_id}",
        json={"result": "合格", "opinion": "整改后复验通过", "acceptor": "监理吴工"},
    ).json()
    assert passed["nodes"][0]["acceptance_result"] == "合格"
    assert passed["nodes"][0]["acceptor"] == "监理吴工"

    client.post(
        f"/api/v1/projects/{project['id']}/nodes",
        json={"title": "洁具安装", "node_date": "2026-11-10", "progress_percent": 95, "operator": "林工"},
    )

    # 完工报验 -> 验收驳回回施工中 -> 再报验 -> 竣工验收通过，公厕恢复
    reviewing = client.post(
        f"/api/v1/projects/{project['id']}/transitions",
        json={"to_status": "待验收", "operator": "林工", "remark": "完工报验"},
    ).json()
    assert reviewing["status"] == "待验收"
    # 待验收阶段不可新增节点
    node_late = client.post(
        f"/api/v1/projects/{project['id']}/nodes",
        json={"title": "额外节点", "node_date": "2026-11-12", "operator": "林工"},
    )
    assert node_late.status_code == 400

    rejected = client.post(
        f"/api/v1/projects/{project['id']}/transitions",
        json={"to_status": "施工中", "operator": "验收组", "remark": "排风仍需调试"},
    ).json()
    assert rejected["status"] == "施工中"
    client.post(
        f"/api/v1/projects/{project['id']}/transitions",
        json={"to_status": "待验收", "operator": "林工", "remark": "整改完成再报验"},
    )
    accepted = client.post(
        f"/api/v1/projects/{project['id']}/transitions",
        json={
            "to_status": "已验收",
            "operator": "验收组周科",
            "remark": "竣工验收通过，资料齐全",
            "actual_cost": 19.8,
        },
    ).json()
    assert accepted["status"] == "已验收"
    assert accepted["accepted_at"] is not None
    assert accepted["accepted_opinion"] == "竣工验收通过，资料齐全"
    assert accepted["actual_cost"] == 19.8
    assert client.get(f"/api/v1/restrooms/{restroom['id']}").json()["status"] == "正常开放"

    # 封存后写操作全部拒绝
    assert client.patch(f"/api/v1/projects/{project['id']}", json={"budget": 21}).status_code == 400
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/transitions",
            json={"to_status": "施工中", "operator": "林工"},
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"/api/v1/projects/{project['id']}/nodes/{node_id}",
            json={"result": "合格", "acceptor": "吴工"},
        ).status_code
        == 400
    )
    assert client.delete(f"/api/v1/projects/{project['id']}").status_code == 400


def test_renovation_delete_restores_restroom_and_filters(client, restroom):
    project = client.post(
        "/api/v1/projects",
        json=_project_payload(
            restroom["id"], planned_start_date="2026-01-01", planned_end_date="2026-02-01"
        ),
    ).json()
    assert client.get(f"/api/v1/restrooms/{restroom['id']}").json()["status"] == "暂停使用"

    # 删除进行中的项目，公厕恢复开放
    deleted = client.delete(f"/api/v1/projects/{project['id']}")
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/restrooms/{restroom['id']}").json()["status"] == "正常开放"

    # 再建一个进行中项目验证过滤：工期超期 + 仅进行中 + 状态
    current = client.post(
        "/api/v1/projects",
        json=_project_payload(
            restroom["id"], planned_start_date="2026-01-01", planned_end_date="2026-02-01"
        ),
    ).json()
    delayed = client.get("/api/v1/projects", params={"delayed": "true"}).json()
    assert delayed["meta"]["total"] == 1
    assert delayed["items"][0]["id"] == current["id"]
    assert delayed["items"][0]["is_delayed"] is True

    open_only = client.get("/api/v1/projects", params={"open_only": "true"}).json()
    assert any(item["id"] == current["id"] for item in open_only["items"])
    by_status = client.get("/api/v1/projects", params={"status": "待施工"}).json()
    assert any(item["id"] == current["id"] for item in by_status["items"])
    by_district = client.get("/api/v1/projects", params={"district": "测试区"}).json()
    assert any(item["id"] == current["id"] for item in by_district["items"])

    # 有改造项目的公厕删除受保护，force 可级联删除
    guarded = client.delete(f"/api/v1/restrooms/{restroom['id']}")
    assert guarded.status_code == 409
    assert "改造项目" in guarded.json()["detail"]
    forced = client.delete(f"/api/v1/restrooms/{restroom['id']}", params={"force": "true"})
    assert forced.status_code == 200
    assert client.get(f"/api/v1/projects/{current['id']}").status_code == 404


def test_renovation_restores_previous_maintenance_status(client, restroom):
    # 公厕原本是维修中，立项停用、验收后应恢复维修中
    client.patch(f"/api/v1/restrooms/{restroom['id']}", json={"status": "维修中"})
    project = client.post("/api/v1/projects", json=_project_payload(restroom["id"])).json()
    assert project["previous_restroom_status"] == "维修中"
    assert client.get(f"/api/v1/restrooms/{restroom['id']}").json()["status"] == "暂停使用"
    for target in ("施工中", "待验收", "已验收"):
        resp = client.post(
            f"/api/v1/projects/{project['id']}/transitions",
            json={"to_status": target, "operator": "林工", "remark": target},
        )
        assert resp.status_code == 200, resp.text
    assert client.get(f"/api/v1/restrooms/{restroom['id']}").json()["status"] == "维修中"
