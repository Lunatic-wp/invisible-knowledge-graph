import re
import datetime

try:
    import spacy
    nlp = spacy.load("zh_core_web_sm")
    SPACY_AVAILABLE = True
except (ImportError, OSError):
    SPACY_AVAILABLE = False

PRESET_NAMES = ["张工", "王总监", "李工"]


def load_text(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_meeting_nodes(meeting_text):
    nodes = []
    decision_keywords = ["要求", "拒绝", "同意", "调整"]
    evidence_keywords = ["因", "根据", "由于"]
    decision_regex = r"(客户.*?要求|技术部.*?确认|最终.*?同意)。*?"
    task_verbs = ["负责", "需", "提交", "完成"]

    current_speaker = None
    lines = meeting_text.strip().split("\n")
    for line in lines:
        if not line.strip():
            continue
        if line.startswith("【"):
            continue

        if "：" in line:
            speaker_part, content = line.split("：", 1)
            current_speaker = speaker_part.strip()
            content = content.strip()
        else:
            content = line.strip()

        sentences = re.split(r"[。！？]", content)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if re.search(decision_regex, sentence):
                nodes.append({"content": sentence, "type": "decision"})

            for keyword in decision_keywords:
                if keyword in sentence and not any(
                    node.get("content") == sentence and node.get("type") == "decision"
                    for node in nodes
                ):
                    nodes.append({"content": sentence, "type": "decision"})
                    break

            for keyword in evidence_keywords:
                if keyword in sentence:
                    nodes.append(
                        {"content": sentence, "type": "evidence", "source": "meeting"}
                    )
                    break

            has_task_verb = any(verb in sentence for verb in task_verbs)
            if has_task_verb:
                names_found = []

                for name in PRESET_NAMES:
                    if name in sentence:
                        names_found.append(name)

                if SPACY_AVAILABLE:
                    doc = nlp(sentence)
                    for ent in doc.ents:
                        if ent.label_ == "PERSON":
                            is_subsumed = False
                            for preset_name in PRESET_NAMES:
                                if preset_name in ent.text and len(preset_name) < len(ent.text):
                                    is_subsumed = True
                                    break
                            if not is_subsumed and ent.text not in names_found:
                                names_found.append(ent.text)

                if "我" in sentence and current_speaker:
                    if current_speaker not in names_found:
                        names_found.append(current_speaker)

                for name in names_found:
                    task_desc = sentence.replace(name, "").replace("我", "").strip()
                    if task_desc:
                        nodes.append({"name": name, "task": task_desc})

    return nodes


def parse_weekday_offset(timestamp_str, weekday_str):
    weekday_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6}
    base_date = datetime.datetime.strptime(timestamp_str.split()[0], "%Y-%m-%d").date()
    target_weekday = weekday_map.get(weekday_str)
    if target_weekday is None:
        return None
    delta_days = (target_weekday - base_date.weekday() + 7) % 7
    if delta_days == 0:
        delta_days = 7
    return (base_date + datetime.timedelta(days=delta_days)).strftime("%Y-%m-%d")


def extract_chat_nodes(chat_text):
    nodes = []
    task_keywords = ["完成", "提交", "负责"]
    deadline_regex = r"(\d{4}-\d{2}-\d{2})"
    warning_keywords = ["记住", "千万别", "别用", "否则", "退回"]
    rule_keywords = ["必须", "直接联系", "走特批", "注意"]
    condition_keywords = ["被拒", "失败", "报错", "退回", "超时", "异常", "错误", "拒绝", "失败了", "出错", "卡壳", "卡住", "驳回", "不通过", "审核不通过", "审批不通过"]
    action_keywords = ["走特批", "直接联系", "找", "联系", "重新提交", "重试", "申请加急", "加急处理", "走绿色通道", "找上级", "打分机", "发邮件", "发工单", "提工单", "找IT", "找运维", "找管理员"]

    lines = chat_text.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        timestamp_str = ""
        author = None
        content = line

        chat_pattern_bracket = r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]\[([^\]]+)\]\s*(.+)$"
        match = re.match(chat_pattern_bracket, line)
        if match:
            timestamp_str = match.group(1)
            author = match.group(2)
            content = match.group(3)
            i += 1
        else:
            chat_pattern_plain = r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+(.+)$"
            match = re.match(chat_pattern_plain, line)
            if match:
                timestamp_str = match.group(1)
                author = match.group(2).strip()
                i += 1
                if i < len(lines):
                    content = lines[i].strip()
                    i += 1
                else:
                    content = ""
            else:
                i += 1
        
        if not content:
            continue

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

        sentences = re.split(r"[。！？]", content)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

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

            has_task_keyword = any(k in sentence for k in task_keywords)
            if has_task_keyword:
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

                deadline_matches = re.findall(deadline_regex, sentence)
                if deadline_matches:
                    base_date = None
                    try:
                        base_date = datetime.datetime.strptime(timestamp_str.split()[0], "%Y-%m-%d").date()
                    except:
                        pass

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
    meeting_nodes = []
    chat_nodes = []

    if meeting_files and len(meeting_files) > 0:
        for meeting_file in meeting_files:
            meeting_text = load_text(meeting_file)
            meeting_nodes.extend(extract_meeting_nodes(meeting_text))

    if chat_files and len(chat_files) > 0:
        for chat_file in chat_files:
            chat_text = load_text(chat_file)
            chat_nodes.extend(extract_chat_nodes(chat_text))

    return meeting_nodes + chat_nodes