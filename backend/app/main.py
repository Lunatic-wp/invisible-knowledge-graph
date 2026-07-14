"""
知识图谱后端服务 - main.py

基于 FastAPI 构建的 RESTful API 服务，提供知识提取、存储和查询功能。
集成 extract_knowledge.py 和 storage.py 模块，实现从会议和聊天文本中提取结构化知识。

API 端点列表：
- GET /                    - 返回前端页面（静态文件服务）
- POST /api/upload         - 上传会议和聊天文件，提取知识并存储
- GET /api/search          - 根据关键词搜索决策链和隐形知识
- GET /api/employee-loss   - 分析员工掌握的决策知识，评估离职风险
- GET /api/health          - 健康检查接口

项目结构：
- frontend/              - 前端静态资源目录（HTML/CSS/JS）
- backend/utils/         - 工具模块目录
  - extract_knowledge.py - 知识提取模块
  - storage.py           - 数据存储模块
- backend/app/main.py    - 后端主服务（当前文件）

注意事项：
- 服务启动时会自动初始化数据库（重建 knowledge.db）
- 文件上传使用临时目录处理，上传完成后自动清理
- CORS 配置为允许所有来源，生产环境需限制具体域名
"""

import os
import sys
import tempfile

# 添加项目根目录到 Python 路径，确保模块导入正确
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, File, UploadFile, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional

# 导入知识提取和存储模块
from utils.extract_knowledge import extract_knowledge
from utils.storage import init_database, save_decision, save_implicit_rules, query_by_keyword, query_by_assignee


# ==================== FastAPI 应用初始化 ====================
# 创建 FastAPI 实例，配置文档信息
app = FastAPI(
    title="知识图谱后端服务",
    description="从会议和聊天文本中提取结构化知识的 RESTful API 服务",
    version="1.0.0"
)

# ==================== CORS 跨域配置 ====================
# 允许前端页面跨域访问后端 API
# 生产环境建议将 allow_origins 限制为具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # 允许所有来源（开发环境）
    allow_credentials=True,        # 允许携带凭证
    allow_methods=["*"],           # 允许所有 HTTP 方法
    allow_headers=["*"],           # 允许所有请求头
)

# ==================== 静态文件服务配置 ====================
# 挂载前端静态资源目录，使前端页面可以访问 CSS 和 JS 文件
frontend_dir = os.path.join(os.path.dirname(__file__), '../../frontend')
app.mount("/css", StaticFiles(directory=os.path.join(frontend_dir, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="js")


# ==================== 首页路由 ====================
@app.get("/")
async def root():
    """
    返回前端主页面
    
    访问根路径时，返回 index.html 作为单页应用入口
    """
    return FileResponse(os.path.join(frontend_dir, "index.html"))


# ==================== 核心转换函数 ====================
def transform_nodes_to_decision_structure(nodes):
    """
    将提取的知识节点转换为决策链结构
    
    转换逻辑：
    1. 将扁平的节点列表按类型分类（决策、依据、任务、客户要求）
    2. 为每个决策关联其依据、任务和客户要求
    3. 从任务内容中识别负责人（通过预设姓名列表匹配）
    4. 建立客户要求与任务的关联（通过客户名称匹配）
    
    Args:
        nodes (list): 知识提取模块返回的节点列表，每个节点包含 type 字段
    
    Returns:
        list: 决策链结构列表，每个元素包含：
              - decision: 决策节点信息
              - evidences: 关联的依据列表
              - tasks: 关联的任务列表（含负责人）
              - clients: 关联的客户要求列表
    
    Note:
        当前负责人识别使用预设姓名列表（张工、王总监、李工），
        后续可优化为基于 spaCy 的实体识别，提高准确性。
    """
    # 按节点类型分类
    decisions = [node for node in nodes if node.get("type") == "decision"]
    evidences = [node for node in nodes if node.get("type") == "evidence"]
    tasks = [node for node in nodes if node.get("type") == "task"]
    requirements = [node for node in nodes if node.get("type") == "requirement"]

    # 预设负责人姓名列表（临时方案，后续可扩展）
    preset_names = ["张工", "王总监", "李工"]

    decision_structures = []

    # 为每个决策构建完整的决策链
    for decision in decisions:
        # 关联依据节点
        decision_evidences = []
        for evidence in evidences:
            decision_evidences.append({
                "content": evidence.get("content"),
                "source_type": evidence.get("source", "meeting")
            })

        # 关联任务节点，并识别负责人
        decision_tasks = []
        for task in tasks:
            assignee = None
            # 通过预设姓名列表匹配任务负责人
            for name in preset_names:
                if name in task.get("content", ""):
                    assignee = name
                    break

            decision_tasks.append({
                "content": task.get("content"),
                "deadline": task.get("deadline"),
                "assignee": assignee,
                "source_type": "chat"  # 任务默认来源为聊天记录
            })

        # 关联客户要求（通过客户名称匹配任务）
        decision_clients = []
        for req in requirements:
            for task in decision_tasks:
                # 匹配条件：客户名称在任务内容中，或任务内容在客户要求中
                if req.get("client") in task.get("content", "") or \
                   task.get("content", "") in req.get("content", ""):
                    decision_clients.append({
                        "name": req.get("client"),
                        "requirement": req.get("content"),
                        "task_content": task.get("content")  # 用于后续关联任务ID
                    })
                    break

        # 构建完整的决策链结构
        decision_structures.append({
            "decision": {"content": decision.get("content"), "meeting_id": 1},
            "evidences": decision_evidences,
            "tasks": decision_tasks,
            "clients": decision_clients
        })

    return decision_structures


# ==================== API 端点 ====================
@app.post("/api/upload", summary="上传会议和聊天文件", tags=["文件处理"])
async def upload_files(
    meeting_files: list[UploadFile] = File(None, description="会议文本文件（支持多个，.txt格式）"),
    chat_files: list[UploadFile] = File(None, description="聊天文本文件（支持多个，.txt格式）")
):
    """
    上传会议和聊天文件，提取知识并存储到数据库
    
    处理流程：
    1. 验证至少上传一个文件
    2. 将上传的文件保存到临时目录
    3. 调用知识提取模块提取结构化知识节点
    4. 将节点转换为决策链结构
    5. 初始化数据库并保存数据
    6. 返回处理结果
    
    Args:
        meeting_files: 会议文本文件列表（可选，支持多个）
        chat_files: 聊天文本文件列表（可选，支持多个）
    
    Returns:
        JSONResponse: 处理结果，包含：
                      - status: 状态（success/error）
                      - message: 处理结果描述
    
    Raises:
        HTTPException(400): 未上传任何文件时抛出
        HTTPException(500): 文件处理或数据库操作失败时抛出
    """
    try:
        # 验证文件上传
        if not meeting_files and not chat_files:
            raise HTTPException(
                status_code=400,
                detail="请至少上传一个会议文件或聊天文件"
            )

        # 使用临时目录处理上传文件（自动清理）
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存会议文件到临时目录
            meeting_file_paths = []
            if meeting_files and len(meeting_files) > 0:
                for i, meeting_file in enumerate(meeting_files):
                    meeting_file_path = os.path.join(temp_dir, f"meeting_{i}.txt")
                    with open(meeting_file_path, "wb") as f:
                        f.write(await meeting_file.read())
                    meeting_file_paths.append(meeting_file_path)

            # 保存聊天文件到临时目录
            chat_file_paths = []
            if chat_files and len(chat_files) > 0:
                for i, chat_file in enumerate(chat_files):
                    chat_file_path = os.path.join(temp_dir, f"chat_{i}.txt")
                    content = await chat_file.read()
                    with open(chat_file_path, "wb") as f:
                        f.write(content)
                    chat_file_paths.append(chat_file_path)

            # 调用知识提取模块
            nodes = extract_knowledge(meeting_file_paths, chat_file_paths)

            # 处理无知识节点的情况
            if len(nodes) == 0:
                return JSONResponse(
                    content={"status": "success", "message": "文件上传成功，但未提取到知识节点"},
                    status_code=200
                )

            # 转换节点为决策链结构
            decision_structures = transform_nodes_to_decision_structure(nodes)

            # 提取隐形知识（规则和警告）
            implicit_rules = [node for node in nodes if node.get("type") in ["rule", "warning"]]

            # 初始化数据库（重建表结构）
            init_database()
            
            # 批量保存决策链数据
            for structure in decision_structures:
                save_decision(
                    structure["decision"],
                    structure["evidences"],
                    structure["tasks"],
                    structure["clients"]
                )

            # 保存隐形知识
            save_implicit_rules(implicit_rules)

        # 构建成功响应
        meeting_count = len(meeting_file_paths) if meeting_file_paths else 0
        chat_count = len(chat_file_paths) if chat_file_paths else 0
        rule_count = len(implicit_rules)
        return JSONResponse(
            content={"status": "success", "message": f"数据解析并入库成功（会议文件: {meeting_count} 个，聊天文件: {chat_count} 个，共提取 {len(nodes)} 个节点，其中隐形知识 {rule_count} 条）"},
            status_code=200
        )

    except HTTPException:
        # 直接抛出已定义的 HTTP 异常
        raise
    except Exception as e:
        # 捕获未知异常，返回 500 错误
        raise HTTPException(
            status_code=500,
            detail=f"文件处理失败: {str(e)}"
        )


@app.get("/api/search", summary="关键词搜索", tags=["查询"])
async def search_by_keyword(
    keyword: str = Query(..., description="搜索关键词")
):
    """
    根据关键词搜索决策链和隐形知识
    
    搜索范围：
    - 决策内容、依据内容、任务内容、客户要求（决策链）
    - 隐形知识内容、相关关键词（隐形知识表）
    
    Args:
        keyword: 搜索关键词（必填）
    
    Returns:
        JSONResponse: 搜索结果，包含：
                      - status: 状态（success/error）
                      - data: 搜索结果数据，包含 decisions 和 implicit_rules
    
    Raises:
        HTTPException(500): 搜索过程中出现错误时抛出
    """
    try:
        # 调用存储模块的搜索函数
        results = query_by_keyword(keyword)

        return JSONResponse(
            content={"status": "success", "data": results},
            status_code=200
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"搜索失败: {str(e)}"
        )


@app.get("/api/employee-loss", summary="员工决策分析", tags=["查询"])
async def employee_loss_analysis(
    name: str = Query(..., description="员工姓名")
):
    """
    分析员工掌握的决策知识，评估离职风险
    
    分析逻辑：
    1. 根据员工姓名查询其负责的所有任务
    2. 统计关联的决策数量（去重）
    3. 估算知识重建耗时（每个任务约需 2 小时）
    4. 根据重建耗时评估风险等级
    
    Args:
        name: 员工姓名（支持模糊匹配）
    
    Returns:
        JSONResponse: 分析结果，包含：
                      - status: 状态（success/error）
                      - data: 分析数据，包含：
                              - employee_name: 员工姓名
                              - decision_count: 关联决策数量
                              - task_count: 关联任务数量
                              - estimated_reconstruction_hours: 预计重建耗时（小时）
                              - tasks: 任务详情列表
    
    Raises:
        HTTPException(500): 分析过程中出现错误时抛出
    """
    try:
        # 查询员工相关的任务和决策
        result = query_by_assignee(name)

        # 计算任务数量和预计重建耗时
        task_count = len(result["tasks"])
        estimated_hours = task_count * 2  # 每个任务预计需要 2 小时重建

        return JSONResponse(
            content={
                "status": "success",
                "data": {
                    "employee_name": name,
                    "decision_count": result["decision_count"],
                    "task_count": task_count,
                    "estimated_reconstruction_hours": estimated_hours,
                    "tasks": result["tasks"]
                }
            },
            status_code=200
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"员工分析失败: {str(e)}"
        )


# ==================== 异常处理 ====================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    全局异常处理器
    
    捕获所有未处理的异常，返回统一格式的错误响应
    
    Args:
        request: 请求对象
        exc: 异常对象
    
    Returns:
        JSONResponse: 错误响应，包含状态、消息和请求路径
    """
    return JSONResponse(
        content={
            "status": "error",
            "message": str(exc),
            "detail": f"请求路径: {request.url.path}"
        },
        status_code=500
    )


# ==================== 健康检查 ====================
@app.get("/api/health", summary="健康检查", tags=["系统"])
async def health_check():
    """
    健康检查接口
    
    用于验证服务是否正常运行，可用于监控和负载均衡
    
    Returns:
        JSONResponse: 健康状态响应
    """
    return JSONResponse(
        content={"status": "healthy", "service": "knowledge-graph-api"},
        status_code=200
    )


# ==================== 服务启动 ====================
if __name__ == "__main__":
    """
    启动 FastAPI 服务
    
    使用 uvicorn 作为 ASGI 服务器运行应用，
    监听 0.0.0.0:8000，支持自动重载（开发模式）。
    
    启动命令：
    python main.py
    
    或使用 uvicorn 直接启动：
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    """
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
