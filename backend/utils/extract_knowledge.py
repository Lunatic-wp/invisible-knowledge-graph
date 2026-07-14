"""
知识提取模块 - extract_knowledge.py

从会议记录和聊天记录中提取结构化知识，包括：
- 决策节点 (decision): 会议中的重要决策
- 依据节点 (evidence): 决策的依据和原因
- 任务分配 (task): 需要完成的任务及截止时间
- 客户要求 (requirement): 客户提出的需求
- 隐形知识 (rule/warning): 职场经验规则和避坑警告

支持的文件格式：
- 会议记录：标准会议纪要格式，包含"客户要求"、"技术部确认"、"最终同意"等关键词
- 聊天记录：两种格式
  1. 带方括号格式：[时间][发送者] 内容
  2. 无方括号格式：时间 发送者\n内容
"""

import re
import datetime

# 尝试加载 spaCy 中文模型用于姓名识别
# 如果加载失败（如未安装或网络问题），降级为预设姓名匹配
try:
    import spacy
    nlp = spacy.load("zh_core_web_sm")
    SPACY_AVAILABLE = True
except (ImportError, OSError):
    SPACY_AVAILABLE = False

# 预设姓名列表（当 spaCy 不可用时使用）
PRESET_NAMES = ["张工", "王总监", "李工"]


def load_text(file_path):
    """
    从文件路径加载文本内容

    Args:
        file_path (str): 文本文件的绝对路径

    Returns:
        str: 文件的完整文本内容

    Raises:
        FileNotFoundError: 文件不存在时抛出
        UnicodeDecodeError: 文件编码不是 UTF-8 时抛出
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_meeting_nodes(meeting_text):
    """
    从会议记录文本中提取知识节点

    提取逻辑：
    1. 决策节点：匹配正则表达式或决策关键词（要求、拒绝、同意、调整）
    2. 依据节点：匹配依据关键词（因、根据、由于）
    3. 任务分配：匹配任务动词（负责、需、提交、完成），并识别负责人姓名

    Args:
        meeting_text (str): 会议记录文本内容

    Returns:
        list: 知识节点列表，每个节点是一个字典，包含以下字段：
              - type: 节点类型 (decision/evidence/task)
              - content: 内容文本
              - name: 任务负责人（仅 task 类型）
              - task: 任务描述（仅 task 类型）
              - source: 来源标识（仅 evidence 类型）

    Notes:
        姓名识别优先级：
        1. 预设姓名列表匹配（PRESET_NAMES）
        2. spaCy 实体识别（PERSON 标签）
        3. 人称代词"我"映射到当前发言者
    """
    nodes = []
    # 决策关键词：用于识别决策节点
    decision_keywords = ["要求", "拒绝", "同意", "调整"]
    # 依据关键词：用于识别决策依据
    evidence_keywords = ["因", "根据", "由于"]
    # 决策正则：匹配典型的决策句式
    decision_regex = r"(客户.*?要求|技术部.*?确认|最终.*?同意)。*?"
    # 任务动词：用于识别任务分配
    task_verbs = ["负责", "需", "提交", "完成"]

    current_speaker = None
    lines = meeting_text.strip().split("\n")
    for line in lines:
        if not line.strip():
            continue
        # 跳过格式标记行（如【会议纪要】）
        if line.startswith("【"):
            continue

        # 解析发言者和内容（格式：发言者：内容）
        if "：" in line:
            speaker_part, content = line.split("：", 1)
            current_speaker = speaker_part.strip()
            content = content.strip()
        else:
            content = line.strip()

        # 按中文标点分割句子
        sentences = re.split(r"[。！？]", content)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # 提取决策节点：优先使用正则匹配
            if re.search(decision_regex, sentence):
                nodes.append({"content": sentence, "type": "decision"})

            # 提取决策节点：关键词匹配（避免重复）
            for keyword in decision_keywords:
                if keyword in sentence and not any(
                    node.get("content") == sentence and node.get("type") == "decision"
                    for node in nodes
                ):
                    nodes.append({"content": sentence, "type": "decision"})
                    break

            # 提取依据节点
            for keyword in evidence_keywords:
                if keyword in sentence:
                    nodes.append(
                        {"content": sentence, "type": "evidence", "source": "meeting"}
                    )
                    break

            # 提取任务分配：识别任务动词并匹配负责人
            has_task_verb = any(verb in sentence for verb in task_verbs)
            if has_task_verb:
                names_found = []

                # 阶段1：匹配预设姓名列表
                for name in PRESET_NAMES:
                    if name in sentence:
                        names_found.append(name)

                # 阶段2：使用 spaCy 实体识别（如果可用）
                if SPACY_AVAILABLE:
                    doc = nlp(sentence)
                    for ent in doc.ents:
                        if ent.label_ == "PERSON":
                            # 避免重复：如果预设姓名是实体的子串，则跳过
                            is_subsumed = False
                            for preset_name in PRESET_NAMES:
                                if preset_name in ent.text and len(preset_name) < len(ent.text):
                                    is_subsumed = True
                                    break
                            if not is_subsumed and ent.text not in names_found:
                                names_found.append(ent.text)

                # 阶段3：处理人称代词"我"
                if "我" in sentence and current_speaker:
                    if current_speaker not in names_found:
                        names_found.append(current_speaker)

                # 生成任务节点
                for name in names_found:
                    task_desc = sentence.replace(name, "").replace("我", "").strip()
                    if task_desc:
                        nodes.append({"name": name, "task": task_desc})

    return nodes


def parse_weekday_offset(timestamp_str, weekday_str):
    """
    根据时间戳和星期字符串计算截止日期

    算法逻辑：
    1. 将星期字符串映射为数字（周一=0, 周二=1, ..., 周日=6）
    2. 计算目标星期与当前日期的天数差
    3. 如果差值为0（本周已过该日），则返回下周同一日期

    Args:
        timestamp_str (str): 时间戳字符串，格式为 "YYYY-MM-DD HH:MM"
        weekday_str (str): 星期字符串，如 "周一", "周二"

    Returns:
        str or None: 计算出的截止日期，格式为 "YYYY-MM-DD"；
                     如果 weekday_str 无效则返回 None

    Example:
        >>> parse_weekday_offset("2026-07-06 09:15", "周三")
        "2026-07-08"
    """
    # 星期映射表
    weekday_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6}

    # 解析基准日期
    base_date = datetime.datetime.strptime(timestamp_str.split()[0], "%Y-%m-%d").date()
    target_weekday = weekday_map.get(weekday_str)

    # 无效的星期字符串
    if target_weekday is None:
        return None

    # 计算天数差
    delta_days = (target_weekday - base_date.weekday() + 7) % 7
    # 如果本周已过该日，设置为下周
    if delta_days == 0:
        delta_days = 7

    return (base_date + datetime.timedelta(days=delta_days)).strftime("%Y-%m-%d")


def extract_chat_nodes(chat_text):
    """
    从聊天记录文本中提取知识节点

    支持两种聊天记录格式：
    格式1（带方括号）: [2026-07-01 10:20][王工] 记住：申请财务系统权限要先抄送李总监
    格式2（无方括号）: 2026-07-06 09:15 王总监\n@李工 客户A刚追加要求...

    提取类型：
    1. 客户要求 (requirement): 匹配"客户[A-Z]"模式
    2. 任务分配 (task): 匹配任务关键词，并提取截止日期
    3. 避坑警告 (warning): 匹配警告关键词（记住、千万别、别用、否则、退回）
    4. 经验规则 (rule): 匹配规则关键词（必须、直接联系、走特批、注意）
    5. 条件触发型经验 (rule): 同时包含条件词和动作词

    Args:
        chat_text (str): 聊天记录文本内容

    Returns:
        list: 知识节点列表，每个节点是一个字典，包含以下字段：
              - type: 节点类型 (requirement/task/warning/rule)
              - content: 内容文本
              - author: 发送者姓名
              - deadline: 截止日期（仅 task 类型）
              - client: 客户名称（仅 requirement 类型）
    """
    nodes = []

    # 任务关键词：用于识别任务分配
    task_keywords = ["完成", "提交", "负责"]
    # 截止日期正则：匹配 YYYY-MM-DD 格式
    deadline_regex = r"(\d{4}-\d{2}-\d{2})"

    # 警告关键词：用于识别避坑警告
    warning_keywords = ["记住", "千万别", "别用", "否则", "退回"]
    # 规则关键词：用于识别经验规则
    rule_keywords = ["必须", "直接联系", "走特批", "注意"]

    # 条件词库：用于条件触发型经验提取（问题/异常状态）
    condition_keywords = [
        "被拒", "失败", "报错", "退回", "超时", "异常", "错误", "拒绝",
        "失败了", "出错", "卡壳", "卡住", "驳回", "不通过", "审核不通过", "审批不通过"
    ]
    # 动作词库：用于条件触发型经验提取（解决方案/操作）
    action_keywords = [
        "走特批", "直接联系", "找", "联系", "重新提交", "重试", "申请加急",
        "加急处理", "走绿色通道", "找上级", "打分机", "发邮件", "发工单",
        "提工单", "找IT", "找运维", "找管理员"
    ]

    lines = chat_text.strip().split("\n")
    i = 0

    # 使用 while 循环支持多行格式（格式2中内容可能跨多行）
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        timestamp_str = ""
        author = None
        content = line

        # 格式1匹配：[时间][发送者] 内容
        chat_pattern_bracket = r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]\[([^\]]+)\]\s*(.+)$"
        match = re.match(chat_pattern_bracket, line)
        if match:
            timestamp_str = match.group(1)
            author = match.group(2)
            content = match.group(3)
            i += 1
        else:
            # 格式2匹配：时间 发送者（内容在下一行）
            chat_pattern_plain = r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+(.+)$"
            match = re.match(chat_pattern_plain, line)
            if match:
                timestamp_str = match.group(1)
                author = match.group(2).strip()
                i += 1
                # 读取下一行作为内容
                if i < len(lines):
                    content = lines[i].strip()
                    i += 1
                else:
                    content = ""
            else:
                # 无法识别的格式，跳过
                i += 1

        # 跳过空内容
        if not content:
            continue

        # ===== 条件触发型经验提取（在分割句子前检查整行内容）=====
        # 设计思路：条件词和动作词可能被标点分割在不同句子中，
        # 因此需要在分割前先检查整行内容是否同时包含两者
        found_condition_action = False
        has_condition = any(cond in content for cond in condition_keywords)
        has_action = any(action in content for action in action_keywords)
        if has_condition and has_action:
            nodes.append({
                "type": "rule",
                "content": content,
                "author": author
            })
            found_condition_action = True

        # ===== 按句子分割提取其他类型 =====
        sentences = re.split(r"[。！？]", content)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # 提取客户要求
            client_match = re.search(r"客户([A-Z])", sentence)
            if client_match:
                client_name = f"客户{client_match.group(1)}"
                nodes.append(
                    {
                        "content": sentence,
                        "client": client_name,
                        "type": "requirement",
                    }
                )

            # 提取任务分配
            has_task_keyword = any(k in sentence for k in task_keywords)
            if has_task_keyword:
                # 阶段1：尝试匹配星期截止日期（如"周三18:00前"）
                weekday_match = re.search(r"(周一|周二|周三|周四|周五|周六|周日)", sentence)
                if weekday_match:
                    deadline = parse_weekday_offset(timestamp_str, weekday_match.group(1))
                    if deadline:
                        nodes.append(
                            {
                                "content": sentence,
                                "type": "task",
                                "deadline": deadline,
                            }
                        )
                        continue

                # 阶段2：尝试匹配日期格式截止日期（如"2026-07-08"）
                deadline_matches = re.findall(deadline_regex, sentence)
                if deadline_matches:
                    base_date = None
                    try:
                        base_date = datetime.datetime.strptime(
                            timestamp_str.split()[0], "%Y-%m-%d"
                        ).date()
                    except:
                        pass

                    # 选择最合适的日期：优先选择大于等于基准日期的最近日期
                    if base_date:
                        best_date = None
                        min_diff = float("inf")
                        for date_str in deadline_matches:
                            try:
                                deadline_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                                diff_days = (deadline_date - base_date).days
                                if diff_days >= 0 and diff_days < min_diff:
                                    min_diff = diff_days
                                    best_date = date_str
                            except:
                                pass
                        if best_date:
                            deadline = best_date
                        else:
                            deadline = deadline_matches[-1]
                    else:
                        deadline = deadline_matches[-1]

                    nodes.append(
                        {
                            "content": sentence,
                            "type": "task",
                            "deadline": deadline,
                        }
                    )

            # 提取避坑警告（优先于经验规则）
            found_warning = False
            for keyword in warning_keywords:
                if keyword in sentence:
                    nodes.append({
                        "type": "warning",
                        "content": sentence,
                        "author": author
                    })
                    found_warning = True
                    break

            # 提取经验规则（排除已提取的警告和条件触发型经验）
            if not found_warning and not found_condition_action:
                for keyword in rule_keywords:
                    if keyword in sentence:
                        nodes.append({
                            "type": "rule",
                            "content": sentence,
                            "author": author
                        })
                        break

    return nodes


def extract_knowledge(meeting_files=None, chat_files=None):
    """
    统一入口：从会议文件和聊天文件中提取知识节点

    Args:
        meeting_files (list or None): 会议记录文件路径列表，默认为 None
        chat_files (list or None): 聊天记录文件路径列表，默认为 None

    Returns:
        list: 所有提取的知识节点列表，包含会议节点和聊天节点

    Note:
        meeting_files 和 chat_files 至少有一个不为空；
        如果两个都为空，返回空列表。
    """
    meeting_nodes = []
    chat_nodes = []

    # 提取会议记录节点
    if meeting_files and len(meeting_files) > 0:
        for meeting_file in meeting_files:
            meeting_text = load_text(meeting_file)
            meeting_nodes.extend(extract_meeting_nodes(meeting_text))

    # 提取聊天记录节点
    if chat_files and len(chat_files) > 0:
        for chat_file in chat_files:
            chat_text = load_text(chat_file)
            chat_nodes.extend(extract_chat_nodes(chat_text))

    return meeting_nodes + chat_nodes