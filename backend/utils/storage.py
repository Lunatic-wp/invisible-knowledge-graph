"""
数据存储模块 - storage.py

基于 SQLite 的数据持久化层，提供知识图谱数据的存储和查询功能。

数据库表结构：
- decisions: 决策节点表，存储会议中的重要决策
- evidences: 依据节点表，存储决策的依据和原因（外键关联 decisions）
- tasks: 任务分配表，存储需要完成的任务（外键关联 decisions）
- clients: 客户要求表，存储客户提出的需求（外键关联 tasks）
- implicit_rules: 隐形知识表，存储职场经验规则和避坑警告

设计特点：
- 使用 SQLite 嵌入式数据库，无需额外部署数据库服务
- 表间通过外键关联，确保数据一致性
- 提供事务支持（通过 commit/rollback）
"""

import sqlite3
import os

# 数据库文件路径（相对路径，运行时解析为当前目录下的 knowledge.db）
DB_PATH = "knowledge.db"


def init_database():
    """
    初始化数据库：创建所有必要的表

    注意事项：
    - 如果数据库文件已存在，将先删除再重新创建（会清空所有数据）
    - 所有表通过外键关联，确保数据完整性
    - 适合在应用启动时或数据重置时调用

    Tables Created:
        decisions: 决策节点表
            - id: 主键，自增
            - content: 决策内容文本（必填）
            - meeting_id: 会议标识（用于关联会议记录）

        evidences: 依据节点表
            - id: 主键，自增
            - decision_id: 关联的决策ID（外键，必填）
            - content: 依据内容文本（必填）
            - source_type: 来源类型（如 meeting/chat，必填）

        tasks: 任务分配表
            - id: 主键，自增
            - content: 任务内容文本（必填）
            - deadline: 截止日期（可选）
            - assignee: 负责人姓名（可选）
            - source_type: 来源类型（默认 'meeting'）
            - decision_id: 关联的决策ID（外键，必填）

        clients: 客户要求表
            - id: 主键，自增
            - name: 客户名称（必填）
            - requirement: 客户要求内容（必填）
            - task_id: 关联的任务ID（外键，必填）

        implicit_rules: 隐形知识表
            - id: 主键，自增
            - content: 知识内容文本（必填）
            - author: 发送者/作者（可选）
            - rule_type: 规则类型（rule/warning，必填）
            - related_keywords: 相关关键词（用于搜索匹配，逗号分隔）

    Returns:
        None
    """
    # 如果数据库已存在，删除后重建（重置数据）
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    # 建立数据库连接
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建决策节点表
    cursor.execute("""
        CREATE TABLE decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            meeting_id INTEGER
        )
    """)

    # 创建依据节点表（外键关联决策）
    cursor.execute("""
        CREATE TABLE evidences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            source_type TEXT NOT NULL,
            FOREIGN KEY (decision_id) REFERENCES decisions(id)
        )
    """)

    # 创建任务分配表（外键关联决策）
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

    # 创建客户要求表（外键关联任务）
    cursor.execute("""
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            requirement TEXT NOT NULL,
            task_id INTEGER NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

    # 创建隐形知识表（独立表，无外键）
    cursor.execute("""
        CREATE TABLE implicit_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            author TEXT,
            rule_type TEXT NOT NULL,
            related_keywords TEXT
        )
    """)

    # 提交事务并关闭连接
    conn.commit()
    conn.close()


def save_implicit_rules(rules):
    """
    批量保存隐形知识规则到数据库

    处理逻辑：
    1. 过滤空规则列表
    2. 为每条规则提取相关关键词（用于后续搜索匹配）
    3. 批量插入 implicit_rules 表

    Args:
        rules (list): 隐形知识规则列表，每个规则是一个字典，包含：
                      - type: 规则类型（rule/warning）
                      - content: 内容文本
                      - author: 发送者（可选）

    Returns:
        None

    Note:
        related_keywords 字段会自动从 content 中提取匹配的关键词，
        用于加速搜索时的匹配效率。
    """
    # 空列表直接返回
    if not rules:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 所有可用的隐形知识关键词（用于提取 related_keywords）
    all_keywords = ["记住", "千万别", "别用", "否则", "退回", "必须", "直接联系", "走特批", "注意"]

    for rule in rules:
        content = rule.get("content", "")
        author = rule.get("author")
        rule_type = rule.get("type", "rule")

        # 提取规则内容中包含的关键词，用于搜索匹配
        found_keywords = [kw for kw in all_keywords if kw in content]
        related_keywords = ",".join(found_keywords)

        # 插入数据库
        cursor.execute(
            "INSERT INTO implicit_rules (content, author, rule_type, related_keywords) VALUES (?, ?, ?, ?)",
            (content, author, rule_type, related_keywords)
        )

    conn.commit()
    conn.close()


def save_decision(decision, evidences=None, tasks=None, clients=None):
    """
    保存决策及其关联的依据、任务和客户要求

    数据关联逻辑：
    1. 先保存决策节点，获取决策ID
    2. 保存依据节点（关联决策ID）
    3. 保存任务节点（关联决策ID），并记录任务ID映射
    4. 保存客户要求（关联任务ID）

    Args:
        decision (dict): 决策节点，包含：
                        - content: 决策内容
                        - meeting_id: 会议标识（可选）
        evidences (list or None): 依据节点列表，每个包含：
                                  - content: 依据内容
                                  - source_type: 来源类型
        tasks (list or None): 任务节点列表，每个包含：
                              - content: 任务内容
                              - deadline: 截止日期（可选）
                              - assignee: 负责人（可选）
                              - source_type: 来源类型（默认 'meeting'）
        clients (list or None): 客户要求列表，每个包含：
                                - name: 客户名称
                                - requirement: 要求内容
                                - task_content: 关联的任务内容（用于匹配任务ID）

    Returns:
        None

    Raises:
        sqlite3.Error: 数据库操作失败时抛出
    """
    # 默认空列表
    evidences = evidences or []
    tasks = tasks or []
    clients = clients or []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 步骤1：保存决策节点
        cursor.execute(
            "INSERT INTO decisions (content, meeting_id) VALUES (?, ?)",
            (decision.get("content"), decision.get("meeting_id"))
        )
        decision_id = cursor.lastrowid

        # 步骤2：保存依据节点
        for evidence in evidences:
            cursor.execute(
                "INSERT INTO evidences (decision_id, content, source_type) VALUES (?, ?, ?)",
                (decision_id, evidence.get("content"), evidence.get("source_type"))
            )

        # 步骤3：保存任务节点，并建立任务内容到ID的映射
        task_id_map = {}
        for task in tasks:
            cursor.execute(
                "INSERT INTO tasks (content, deadline, assignee, source_type, decision_id) VALUES (?, ?, ?, ?, ?)",
                (task.get("content"), task.get("deadline"), task.get("assignee"),
                 task.get("source_type", "meeting"), decision_id)
            )
            task_id_map[task.get("content")] = cursor.lastrowid

        # 步骤4：保存客户要求（通过任务内容匹配任务ID）
        for client in clients:
            task_content = client.get("task_content")
            task_id = task_id_map.get(task_content)
            if task_id:
                cursor.execute(
                    "INSERT INTO clients (name, requirement, task_id) VALUES (?, ?, ?)",
                    (client.get("name"), client.get("requirement"), task_id)
                )

        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_by_assignee(assignee_name):
    """
    根据员工姓名查询其负责的任务和关联的决策

    查询逻辑：
    - 通过 tasks 表的 assignee 字段模糊匹配员工姓名
    - LEFT JOIN decisions 表获取关联的决策信息
    - 去重统计关联的决策数量

    Args:
        assignee_name (str): 员工姓名（支持模糊匹配）

    Returns:
        dict: 查询结果字典，包含：
              - assignee_name: 查询的员工姓名
              - decision_count: 关联的决策数量（去重后）
              - tasks: 任务列表，每个任务包含：
                       - id: 任务ID
                       - content: 任务内容
                       - deadline: 截止日期
                       - source_type: 来源类型
                       - decision_id: 关联的决策ID
                       - decision_content: 关联的决策内容

    Example:
        >>> query_by_assignee("李工")
        {
            "assignee_name": "李工",
            "decision_count": 3,
            "tasks": [
                {"id": 1, "content": "完成API兼容性测试", ...}
            ]
        }
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 查询员工相关的任务和关联决策
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
    """
    根据关键词搜索决策链和隐形知识

    查询逻辑：
    1. 决策链查询：
       - 通过 LEFT JOIN 关联 decisions、evidences、tasks、clients 四张表
       - 在决策内容、依据内容、任务内容、客户要求中进行模糊匹配
       - 将查询结果重组为决策链结构（决策 -> 依据/任务/客户）

    2. 隐形知识查询：
       - 查询 implicit_rules 表
       - 在内容和相关关键词中进行模糊匹配

    Args:
        keyword (str): 搜索关键词

    Returns:
        dict: 查询结果字典，包含：
              - decisions: 决策链列表，每个决策链包含：
                           - id: 决策ID
                           - content: 决策内容
                           - meeting_id: 会议ID
                           - evidences: 依据列表
                           - tasks: 任务列表（每个任务包含 clients 子列表）
              - implicit_rules: 隐形知识列表，每个包含：
                                - id: 规则ID
                                - content: 内容文本
                                - author: 作者
                                - rule_type: 规则类型
                                - related_keywords: 相关关键词

    Note:
        决策链查询结果会自动去重，避免同一决策被多次返回。
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ===== 决策链查询 =====
    # 使用 LEFT JOIN 关联所有相关表，支持关键词在任意字段中匹配
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

    # 重组决策链结构（去重）
    result = []
    current_decision = None

    for row in rows:
        (decision_id, decision_content, meeting_id,
         evidence_id, evidence_content, evidence_source_type,
         task_id, task_content, deadline, assignee, task_source_type,
         client_id, client_name, client_requirement) = row

        # 创建新的决策链（如果决策ID不同）
        if current_decision is None or current_decision["id"] != decision_id:
            current_decision = {
                "id": decision_id,
                "content": decision_content,
                "meeting_id": meeting_id,
                "evidences": [],
                "tasks": []
            }
            result.append(current_decision)

        # 添加依据（去重）
        if evidence_id:
            evidence_exists = any(e["id"] == evidence_id for e in current_decision["evidences"])
            if not evidence_exists:
                current_decision["evidences"].append({
                    "id": evidence_id,
                    "content": evidence_content,
                    "source_type": evidence_source_type
                })

        # 添加任务（去重）
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
                # 获取已存在的任务（用于添加客户）
                task = next(t for t in current_decision["tasks"] if t["id"] == task_id)

            # 添加客户（去重）
            if client_id:
                client_exists = any(c["id"] == client_id for c in task["clients"])
                if not client_exists:
                    task["clients"].append({
                        "id": client_id,
                        "name": client_name,
                        "requirement": client_requirement
                    })

    # ===== 隐形知识查询 =====
    cursor.execute("""
        SELECT id, content, author, rule_type, related_keywords
        FROM implicit_rules
        WHERE content LIKE ? OR related_keywords LIKE ?
    """, (f"%{keyword}%", f"%{keyword}%"))

    implicit_rules_rows = cursor.fetchall()
    conn.close()

    # 转换隐形知识结果
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