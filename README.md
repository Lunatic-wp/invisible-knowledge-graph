# 职场隐形知识图谱

从会议记录和聊天记录中自动提取结构化知识，构建职场隐形知识图谱。

## 功能特性

### 核心功能
- **知识提取**：从会议记录和聊天记录中提取决策节点、依据节点、责任人、任务分配和客户要求
- **隐形知识挖掘**：识别职场经验规则和避坑警告
- **关键词搜索**：支持按关键词检索决策链和隐形知识
- **离职员工分析**：分析员工掌握的核心知识，评估离职风险

### 隐形知识提取类型
- **经验规则 (Rule)**：包含"必须"、"直接联系"、"走特批"、"注意"等关键词
- **避坑警告 (Warning)**：包含"记住"、"千万别"、"别用"、"否则"、"退回"等关键词
- **条件触发型经验**：同时包含条件词（被拒、失败、报错、超时等）和动作词（走特批、直接联系、找等）

## 技术栈

### 后端
- **框架**: FastAPI
- **数据库**: SQLite
- **NLP**: spaCy (中文分词)
- **服务器**: Uvicorn

### 前端
- **HTML5** + **CSS3** + **JavaScript** (原生)
- **Flexbox** 布局

## 项目结构

```
invisible-knowledge-graph/
├── backend/
│   ├── app/
│   │   └── main.py          # FastAPI 后端服务入口
│   └── utils/
│       ├── extract_knowledge.py  # 知识提取模块
│       └── storage.py            # 数据库存储模块
├── frontend/
│   ├── index.html           # 前端页面
│   ├── css/
│   │   └── style.css        # 样式文件
│   └── js/
│       └── app.js           # 前端逻辑
├── chat.txt                 # 示例聊天记录
├── chat_rules.txt           # 示例隐形知识聊天记录
├── meeting.txt              # 示例会议记录
├── requirements.txt         # Python 依赖
└── .gitignore               # Git 忽略配置
```

## 安装与运行

### 环境要求
- Python 3.8+
- pip (Python 包管理工具)

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd invisible-knowledge-graph
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **下载 spaCy 中文模型**
   ```bash
   python -m spacy download zh_core_web_sm
   
   # 如果下载失败，尝试直接安装
   pip install https://github.com/explosion/spacy-models/releases/download/zh_core_web_sm-3.8.0/zh_core_web_sm-3.8.0-py3-none-any.whl
   ```

### 启动服务

```bash
cd backend/app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

访问 `http://localhost:8000/` 查看界面。

## API 接口

### 文件上传
**POST** `/api/upload`

上传会议记录和聊天记录文件。

### 关键词搜索
**GET** `/api/search?keyword=<关键词>`

搜索决策链和隐形知识。

### 离职员工分析
**GET** `/api/employee-loss?name=<员工姓名>`

分析员工掌握的核心知识。

### 健康检查
**GET** `/api/health`

检查服务状态。

## 使用说明

1. **上传文件**：点击或拖拽上传 `.txt` 格式的会议记录和聊天记录
2. **搜索知识**：输入关键词检索决策链和隐形知识
3. **分析员工**：输入员工姓名评估离职风险

## 支持的文件格式

### 会议记录格式
```
2026-07-05 10:00-11:30 项目例会

一、会议议题
1. 客户A周末免运费需求评估

二、会议决策
1. 技术部确认：支持周末免运费功能，预计开发周期3天
2. 最终同意：按客户要求执行，张工负责技术方案设计

三、任务分配
1. 张工：提交技术方案文档，截止2026-07-08
2. 李工：完成API兼容性测试，截止2026-07-10
```

### 聊天记录格式（带方括号）
```
[2026-07-01 10:20][王工] 记住：申请财务系统权限要先抄送李总监，否则自动被拒。
[2026-07-02 14:15][HR张] 新同事注意：OA系统部门编码必须填'FIN-003'，填错会退回三次。
```

### 聊天记录格式（无方括号）
```
2026-07-06 09:15 王总监
@李工 客户A刚追加要求：必须支持周末免运费，周三18:00前提交需求文档！
```

## 许可证

本项目仅用于参赛展示，未经授权禁止商用或抄袭

## 贡献

欢迎提交 Issue 和 Pull Request！