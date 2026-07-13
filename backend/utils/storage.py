import sqlite3
import os

DB_PATH = "knowledge.db"


def init_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            meeting_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE evidences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            source_type TEXT NOT NULL,
            FOREIGN KEY (decision_id) REFERENCES decisions(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            deadline TEXT,
            assignee TEXT,
            source_type TEXT NOT NULL DEFAULT 'meeting',
            decision_id INTEGER NOT NULL,
            FOREIGN KEY (decision_id) REFERENCES decisions(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            requirement TEXT NOT NULL,
            task_id INTEGER NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE implicit_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            author TEXT,
            rule_type TEXT NOT NULL,
            related_keywords TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_implicit_rules(rules):
    if not rules:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for rule in rules:
        content = rule.get("content", "")
        author = rule.get("author")
        rule_type = rule.get("type", "rule")
        
        all_keywords = ["记住", "千万别", "别用", "否则", "退回", "必须", "直接联系", "走特批", "注意"]
        found_keywords = [kw for kw in all_keywords if kw in content]
        related_keywords = ",".join(found_keywords)

        cursor.execute("INSERT INTO implicit_rules (content, author, rule_type, related_keywords) VALUES (?, ?, ?, ?)",
                       (content, author, rule_type, related_keywords))

    conn.commit()
    conn.close()


def save_decision(decision, evidences=None, tasks=None, clients=None):
    evidences = evidences or []
    tasks = tasks or []
    clients = clients or []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("INSERT INTO decisions (content, meeting_id) VALUES (?, ?)",
                   (decision.get("content"), decision.get("meeting_id")))
    decision_id = cursor.lastrowid

    for evidence in evidences:
        cursor.execute("INSERT INTO evidences (decision_id, content, source_type) VALUES (?, ?, ?)",
                       (decision_id, evidence.get("content"), evidence.get("source_type")))

    task_id_map = {}
    for task in tasks:
        cursor.execute("INSERT INTO tasks (content, deadline, assignee, source_type, decision_id) VALUES (?, ?, ?, ?, ?)",
                       (task.get("content"), task.get("deadline"), task.get("assignee"), task.get("source_type", "meeting"), decision_id))
        task_id_map[task.get("content")] = cursor.lastrowid

    for client in clients:
        task_content = client.get("task_content")
        task_id = task_id_map.get(task_content)
        if task_id:
            cursor.execute("INSERT INTO clients (name, requirement, task_id) VALUES (?, ?, ?)",
                           (client.get("name"), client.get("requirement"), task_id))

    conn.commit()
    conn.close()


def query_by_assignee(assignee_name):
    """
    根据员工姓名查询其相关的决策和任务
    :param assignee_name: 员工姓名
    :return: 包含决策数量和任务信息的字典
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.id, t.content, t.deadline, t.source_type,
               d.id as decision_id, d.content as decision_content
        FROM tasks t
        LEFT JOIN decisions d ON t.decision_id = d.id
        WHERE t.assignee LIKE ?
    """, (f"%{assignee_name}%",))

    rows = cursor.fetchall()
    conn.close()

    task_list = []
    decision_ids = set()

    for row in rows:
        task_id, task_content, deadline, source_type, decision_id, decision_content = row
        task_list.append({
            "id": task_id,
            "content": task_content,
            "deadline": deadline,
            "source_type": source_type,
            "decision_id": decision_id,
            "decision_content": decision_content
        })
        if decision_id:
            decision_ids.add(decision_id)

    return {
        "assignee_name": assignee_name,
        "decision_count": len(decision_ids),
        "tasks": task_list
    }


def query_by_keyword(keyword):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.id as decision_id, d.content as decision_content, d.meeting_id,
               e.id as evidence_id, e.content as evidence_content, e.source_type as evidence_source_type,
               t.id as task_id, t.content as task_content, t.deadline, t.assignee, t.source_type as task_source_type,
               c.id as client_id, c.name as client_name, c.requirement as client_requirement
        FROM decisions d
        LEFT JOIN evidences e ON d.id = e.decision_id
        LEFT JOIN tasks t ON d.id = t.decision_id
        LEFT JOIN clients c ON t.id = c.task_id
        WHERE d.content LIKE ? OR e.content LIKE ? OR t.content LIKE ? OR c.requirement LIKE ?
    """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))

    rows = cursor.fetchall()

    result = []
    current_decision = None

    for row in rows:
        (decision_id, decision_content, meeting_id,
         evidence_id, evidence_content, evidence_source_type,
         task_id, task_content, deadline, assignee, task_source_type,
         client_id, client_name, client_requirement) = row

        if current_decision is None or current_decision["id"] != decision_id:
            current_decision = {
                "id": decision_id,
                "content": decision_content,
                "meeting_id": meeting_id,
                "evidences": [],
                "tasks": []
            }
            result.append(current_decision)

        if evidence_id:
            evidence_exists = any(e["id"] == evidence_id for e in current_decision["evidences"])
            if not evidence_exists:
                current_decision["evidences"].append({
                    "id": evidence_id,
                    "content": evidence_content,
                    "source_type": evidence_source_type
                })

        if task_id:
            task_exists = any(t["id"] == task_id for t in current_decision["tasks"])
            if not task_exists:
                task = {
                    "id": task_id,
                    "content": task_content,
                    "deadline": deadline,
                    "assignee": assignee,
                    "source_type": task_source_type,
                    "clients": []
                }
                current_decision["tasks"].append(task)
            else:
                task = next(t for t in current_decision["tasks"] if t["id"] == task_id)

            if client_id:
                client_exists = any(c["id"] == client_id for c in task["clients"])
                if not client_exists:
                    task["clients"].append({
                        "id": client_id,
                        "name": client_name,
                        "requirement": client_requirement
                    })

    cursor.execute("""
        SELECT id, content, author, rule_type, related_keywords
        FROM implicit_rules
        WHERE content LIKE ? OR related_keywords LIKE ?
    """, (f"%{keyword}%", f"%{keyword}%"))

    implicit_rules_rows = cursor.fetchall()
    conn.close()

    implicit_rules = []
    for row in implicit_rules_rows:
        rule_id, content, author, rule_type, related_keywords = row
        implicit_rules.append({
            "id": rule_id,
            "content": content,
            "author": author,
            "rule_type": rule_type,
            "related_keywords": related_keywords
        })

    return {
        "decisions": result,
        "implicit_rules": implicit_rules
    }