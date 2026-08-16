"""端到端 API 测试：上传→解析→问答→总结→出题→判分→错题本。"""
import json


import time


def _upload_txt(client, content="Python 装饰器是接收函数并返回新函数的可调用对象。\n装饰器语法用 @ 符号。", name="python_notes.md"):
    resp = client.post(
        "/api/documents/upload",
        files={"file": (name, content.encode("utf-8"), "text/markdown")},
    )
    assert resp.status_code == 200, resp.text
    return _wait_ready(client, resp.json()["id"])


def _wait_ready(client, doc_id, timeout=15):
    """后台解析为异步执行，轮询等待处理完成。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        d = client.get(f"/api/documents/{doc_id}").json()
        if d["status"] != "pending" and d["status"] != "processing":
            assert d["status"] == "ready", f"处理失败: {d.get('error')}"
            return d
        time.sleep(0.2)
    raise AssertionError("等待资料处理超时")


def test_upload_reject_unsupported_type(client):
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("a.exe", b"MZ", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_upload_list_detail_delete(client):
    doc = _upload_txt(client)
    assert doc["status"] == "ready"  # TestClient 同步执行后台任务
    assert doc["file_type"] == "md"
    assert doc["chunk_count"] >= 1

    lst = client.get("/api/documents").json()
    assert any(d["id"] == doc["id"] for d in lst)

    detail = client.get(f"/api/documents/{doc['id']}").json()
    assert detail["original_name"] == "python_notes.md"
    assert len(detail["chapters"]) >= 1

    resp = client.delete(f"/api/documents/{doc['id']}")
    assert resp.status_code == 200
    assert client.get(f"/api/documents/{doc['id']}").status_code == 404


def test_chat_flow_with_evidence(client, app_env):
    _upload_txt(client)
    app_env["set_reply"]("装饰器本质是函数[1]。")

    resp = client.post(
        "/api/chat",
        json={"message": "什么是装饰器？"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_evidence"] is True
    assert len(data["sources"]) >= 1
    assert data["sources"][0]["document_name"] == "python_notes.md"

    conv_id = data["conversation_id"]
    hist = client.get(f"/api/chat/conversations/{conv_id}").json()
    assert len(hist["messages"]) == 2
    resp2 = client.post(
        "/api/chat",
        json={"conversation_id": conv_id, "message": "再问一个"},
    )
    assert resp2.status_code == 200


def test_summary_generate_and_list(client, app_env):
    doc = _upload_txt(client)
    app_env["set_reply"](
        json.dumps(
            {
                "core_points": "核心1",
                "key_concepts": "概念1",
                "pitfalls": "易错1",
                "memory_items": "记忆1",
                "short_summary": "总结1",
            },
            ensure_ascii=False,
        )
    )
    resp = client.post(
        "/api/summaries/generate",
        json={"document_id": doc["id"], "chapter_path": ""},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["core_points"] == "核心1"
    assert data["title"] == "python_notes.md · 全文"

    lst = client.get(f"/api/summaries/document/{doc['id']}").json()
    assert len(lst) == 1


def test_quiz_generate_submit_and_wrong_book(client, app_env):
    doc = _upload_txt(client)
    app_env["set_reply"](
        json.dumps(
            [
                {
                    "type": "choice",
                    "question": "装饰器的语法符号是？",
                    "options": ["A. @", "B. #"],
                    "answer": "A",
                    "explanation": "装饰器使用 @ 语法。",
                    "difficulty": "easy",
                    "knowledge_point": "装饰器",
                },
                {
                    "type": "true_false",
                    "question": "生成器使用 yield。",
                    "options": [],
                    "answer": "正确",
                    "explanation": "yield 是生成器标志。",
                    "difficulty": "easy",
                    "knowledge_point": "生成器",
                },
            ],
            ensure_ascii=False,
        )
    )
    resp = client.post(
        "/api/quizzes/generate",
        json={"document_id": doc["id"], "count": 2, "types": ["choice", "true_false"]},
    )
    assert resp.status_code == 200, resp.text
    qs = resp.json()
    qid = qs["id"]
    assert len(qs["questions"]) == 2
    q1, q2 = qs["questions"]

    submit = client.post(
        f"/api/quizzes/{qid}/submit",
        json={
            "answers": [
                {"question_id": q1["id"], "user_answer": "B"},
                {"question_id": q2["id"], "user_answer": "正确"},
            ]
        },
    )
    assert submit.status_code == 200, submit.text
    result = submit.json()
    assert result["correct_count"] == 1
    assert result["total_count"] == 2
    assert result["wrong_question_count"] == 1

    wrongs = client.get("/api/wrong-questions").json()
    assert len(wrongs) == 1
    wq = wrongs[0]
    assert wq["question"] == "装饰器的语法符号是？"
    assert wq["correct_answer"] == "A"
    assert wq["my_answer"] == "B"
    assert wq["wrong_count"] == 1

    redo = client.post(f"/api/wrong-questions/{wq['id']}/redo", json={"is_correct": False})
    assert redo.status_code == 200
    assert redo.json()["wrong_count"] == 2

    client.post(f"/api/wrong-questions/{wq['id']}/redo", json={"is_correct": True})
    assert client.get("/api/wrong-questions").json() == []


def test_short_answer_self_evaluation(client, app_env):
    doc = _upload_txt(client)
    app_env["set_reply"](
        json.dumps(
            [
                {
                    "type": "short_answer",
                    "question": "什么是装饰器？",
                    "options": [],
                    "answer": "接收函数并返回新函数的可调用对象。",
                    "explanation": "装饰器用于扩展函数。",
                    "difficulty": "medium",
                    "knowledge_point": "装饰器",
                }
            ],
            ensure_ascii=False,
        )
    )
    qs = client.post(
        "/api/quizzes/generate",
        json={"document_id": doc["id"], "count": 1, "types": ["short_answer"]},
    ).json()
    qid = qs["questions"][0]["id"]

    r1 = client.post(
        f"/api/quizzes/{qs['id']}/submit",
        json={"answers": [{"question_id": qid, "user_answer": "我的答案", "self_evaluated": True}]},
    ).json()
    assert r1["correct_count"] == 1
    assert client.get("/api/wrong-questions").json() == []

    r2 = client.post(
        f"/api/quizzes/{qs['id']}/submit",
        json={"answers": [{"question_id": qid, "user_answer": "错误答案", "self_evaluated": False}]},
    ).json()
    assert r2["wrong_question_count"] == 1
    assert len(client.get("/api/wrong-questions").json()) == 1


def test_chat_stream_sse(client, app_env):
    """SSE 流式对话：delta 事件 + done 事件 + 消息持久化。"""
    _upload_txt(client)
    app_env["set_reply"]("流式回答第一段。第二段。")

    resp = client.post("/api/chat/stream", json={"message": "什么是装饰器？"})
    assert resp.status_code == 200, resp.text
    assert "text/event-stream" in resp.headers.get("content-type", "")

    body = resp.text
    assert '"type": "delta"' in body
    assert '"type": "done"' in body

    # 流结束后消息已持久化（user + assistant 完整内容）
    convs = client.get("/api/chat/conversations").json()
    assert len(convs) == 1
    hist = client.get(f"/api/chat/conversations/{convs[0]['id']}").json()
    roles = [m["role"] for m in hist["messages"]]
    assert roles == ["user", "assistant"]
    assert hist["messages"][-1]["content"] == "流式回答第一段。第二段。"


def test_chat_stream_error_keeps_user_message(client, app_env):
    """AI 流式失败时：用户消息已持久化，前端收到 error 事件。"""
    _upload_txt(client)
    app_env["set_reply"](lambda messages: (_ for _ in ()).throw(RuntimeError("模拟AI故障")))

    resp = client.post("/api/chat/stream", json={"message": "会失败的问题"})
    assert resp.status_code == 200
    assert '"type": "error"' in resp.text

    convs = client.get("/api/chat/conversations").json()
    assert len(convs) == 1
    hist = client.get(f"/api/chat/conversations/{convs[0]['id']}").json()
    assert hist["messages"][0]["role"] == "user"
    assert hist["messages"][0]["content"] == "会失败的问题"


def test_document_content_preview(client):
    """全文预览接口：返回章节与正文。"""
    doc = _upload_txt(client)
    resp = client.get(f"/api/documents/{doc['id']}/content")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["original_name"] == "python_notes.md"
    assert len(data["sections"]) >= 1
    assert "装饰器" in data["sections"][0]["text"]
    assert resp.headers["content-type"].startswith("application/json")


def test_document_content_not_ready(client):
    resp = client.get("/api/documents/99999/content")
    assert resp.status_code == 404


def test_document_subject_flow(client, app_env):
    """学科：上传带 subject → 列表含 subject → PATCH 修改 → subjects 统计。"""
    # 上传带学科
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("math.md", "微积分基础内容。".encode(), "text/markdown")},
        data={"subject": "数学"},
    )
    assert resp.status_code == 200, resp.text
    doc = _wait_ready(client, resp.json()["id"])
    assert doc["subject"] == "数学"

    # 列表包含 subject
    lst = client.get("/api/documents").json()
    assert any(d["id"] == doc["id"] and d["subject"] == "数学" for d in lst)

    # 修改学科
    upd = client.patch(f"/api/documents/{doc['id']}", json={"subject": "高数"})
    assert upd.status_code == 200
    assert upd.json()["subject"] == "高数"

    # subjects 统计
    subs = client.get("/api/documents/subjects").json()
    assert any(s["subject"] == "高数" and s["count"] == 1 for s in subs)

    # 按学科检索过滤（向量元数据同步更新）
    app_env["set_reply"]("高数回答")
    resp = client.post(
        "/api/chat/stream",
        json={"message": "微积分是什么？", "subject": "高数"},
    )
    assert resp.status_code == 200
    # 未匹配学科时不报错（空结果）
    resp2 = client.post(
        "/api/chat/stream",
        json={"message": "微积分是什么？", "subject": "不存在的学科"},
    )
    assert resp2.status_code == 200


def test_settings_endpoint(client):
    data = client.get("/api/settings").json()
    assert data["ai_provider"] == "fake"
    assert data["chat_configured"] is True
    assert "document_count" in data


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}