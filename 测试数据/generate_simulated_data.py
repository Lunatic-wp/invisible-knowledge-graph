# 用于测试生成模拟的企业微信聊天记录

import random
from datetime import datetime, timedelta

# 1. 配置数据源
# 核心隐形知识（占比约 10%）
IMPLICIT_KNOWLEDGE = [
    "记住：申请财务系统权限要先抄送李总监，否则自动被拒。",
    "新同事注意：OA系统部门编码必须填'FIN-003'，填错会退回三次。",
    "ERP权限申请被拒3次以上？直接联系张经理（分机8001）走特批。",
    "别用个人邮箱申请！必须用企业微信里的'权限申请'模板。",
    "报销单贴票必须用胶水，别用订书机，财务会直接打回。",
    "注意：请假超过3天需要提前一周在系统提交。"
]

# 日常无用闲聊（占比约 90%）
NOISE_CHAT = [
    "大家早上好！", "早啊，今天天气不错。", "中午大家一起去楼下吃黄焖鸡吗？",
    "下午的周会推迟半小时哈，会议室被占了。", "又是搬砖的一天。", "收到。",
    "昨天那个需求文档谁写的？格式不太对。", "是我写的，我马上改。",
    "提醒：本周五下午3点全员培训，不要迟到。", "好的。", "下班有人一起打羽毛球吗？",
    "我去！", "这个bug修好了吗？", "还在排查中，有点复杂。", "好的，辛苦了！"
]

# 模拟员工名单
USERS = ["王工", "李工", "HR张", "刘经理", "赵工", "新员工小陈"]

def generate_chat_log(num_messages=100, output_file="simulated_chatlog.txt"):
    """
    生成模拟的企业微信聊天记录
    :param num_messages: 生成的消息总条数
    :param output_file: 输出文件名
    """
    logs = []
    # 设定一个起始时间
    current_time = datetime(2026, 7, 1, 9, 0, 0)
    
    for _ in range(num_messages):
        # 每次消息时间随机增加 1~15 分钟
        current_time += timedelta(minutes=random.randint(1, 15))
        time_str = current_time.strftime("%Y-%m-%d %H:%M")
        user = random.choice(USERS)
        
        # 10% 的概率生成隐形知识，90% 的概率生成闲聊
        if random.random() < 0.1:
            content = random.choice(IMPLICIT_KNOWLEDGE)
        else:
            content = random.choice(NOISE_CHAT)
            
        logs.append(f"[{time_str}][{user}] {content}")
        
    # 写入文件
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(logs))
        
    print(f" 成功生成 {num_messages} 条模拟聊天记录，已保存至 {output_file}")

if __name__ == "__main__":
    # 默认生成 200 条消息，你可以修改数字进行压力测试
    generate_chat_log(200)