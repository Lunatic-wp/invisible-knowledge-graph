"""
知识图谱后端服务 - main.py

基于 FastAPI 构建的 RESTful API 服务，提供知识提取、存储和查询功能。
集成 extract_knowledge.py 和 storage.py 模块，实现从会议和聊天文本中提取结构化知识。
"""

import os
import sys
import tempfile

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, File, UploadFile, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional

from utils.extract_knowledge import extract_knowledge
from utils.storage import init_database, save_decision, save_implicit_rules, query_by_keyword, query_by_assignee


app = FastAPI(
    title="知识图谱后端服务",
    description="从会议和聊天文本中提取结构化知识的 RESTful API 服务",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = os.path.join(os.path.dirname(__file__), '../../frontend')
app.mount("/css", StaticFiles(directory=os.path.join(frontend_dir, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="js")


@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_dir, "index.html"))


def transform_nodes_to_decision_structure(nodes):
    decisions = [node for node in nodes if node.get("type") == "decision"]
    evidences = [node for node in nodes if node.get("type") == "evidence"]
    tasks = [node for node in nodes if node.get("type") == "task"]
    requirements = [node for node in nodes if node.get("type") == "requirement"]

    preset_names = ["张工", "王总监", "李工"]

    decision_structures = []

    for decision in decisions:
        decision_evidences = []
        for evidence in evidences:
            decision_evidences.append({
                "content": evidence.get("content"),
                "source_type": evidence.get("source", "meeting")
            })

        decision_tasks = []
        for task in tasks:
            assignee = None
            for name in preset_names:
                if name in task.get("content", ""):
                    assignee = name
                    break

            decision_tasks.append({
                "content": task.get("content"),
                "deadline": task.get("deadline"),
                "assignee": assignee,
                "source_type": "chat"
            })

        decision_clients = []
        for req in requirements:
            for task in decision_tasks:
                if req.get("client") in task.get("content", "") or \
                   task.get("content", "") in req.get("content", ""):
                    decision_clients.append({
                        "name": req.get("client"),
                        "requirement": req.get("content"),
                        "task_content": task.get("content")
                    })
                    break

        decision_structures.append({
            "decision": {"content": decision.get("content"), "meeting_id": 1},
            "evidences": decision_evidences,
            "tasks": decision_tasks,
            "clients": decision_clients
        })

    return decision_structures


@app.post("/api/upload", summary="上传会议和聊天文件", tags=["文件处理"])
async def upload_files(
    meeting_files: list[UploadFile] = File(None, description="会议文本文件（支持多个，.txt格式）"),
    chat_files: list[UploadFile] = File(None, description="聊天文本文件（支持多个，.txt格式）")
):
    try:
        if not meeting_files and not chat_files:
            raise HTTPException(
                status_code=400,
                detail="请至少上传一个会议文件或聊天文件"
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            meeting_file_paths = []
            if meeting_files and len(meeting_files) > 0:
                for i, meeting_file in enumerate(meeting_files):
                    meeting_file_path = os.path.join(temp_dir, f"meeting_{i}.txt")
                    with open(meeting_file_path, "wb") as f:
                        f.write(await meeting_file.read())
                    meeting_file_paths.append(meeting_file_path)

            chat_file_paths = []
            if chat_files and len(chat_files) > 0:
                for i, chat_file in enumerate(chat_files):
                    chat_file_path = os.path.join(temp_dir, f"chat_{i}.txt")
                    content = await chat_file.read()
                    with open(chat_file_path, "wb") as f:
                        f.write(content)
                    chat_file_paths.append(chat_file_path)

            nodes = extract_knowledge(meeting_file_paths, chat_file_paths)

            if len(nodes) == 0:
                return JSONResponse(
                    content={"status": "success", "message": "文件上传成功，但未提取到知识节点"},
                    status_code=200
                )

            decision_structures = transform_nodes_to_decision_structure(nodes)

            implicit_rules = [node for node in nodes if node.get("type") in ["rule", "warning"]]

            init_database()
            for structure in decision_structures:
                save_decision(
                    structure["decision"],
                    structure["evidences"],
                    structure["tasks"],
                    structure["clients"]
                )

            save_implicit_rules(implicit_rules)

        meeting_count = len(meeting_file_paths) if meeting_file_paths else 0
        chat_count = len(chat_file_paths) if chat_file_paths else 0
        rule_count = len(implicit_rules)
        return JSONResponse(
            content={"status": "success", "message": f"数据解析并入库成功（会议文件: {meeting_count} 个，聊天文件: {chat_count} 个，共提取 {len(nodes)} 个节点，其中隐形知识 {rule_count} 条）"},
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"文件处理失败: {str(e)}"
        )


@app.get("/api/search", summary="关键词搜索", tags=["查询"])
async def search_by_keyword(
    keyword: str = Query(..., description="搜索关键词")
):
    try:
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
    try:
        result = query_by_assignee(name)

        task_count = len(result["tasks"])
        estimated_hours = task_count * 2

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


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        content={
            "status": "error",
            "message": str(exc),
            "detail": f"请求路径: {request.url.path}"
        },
        status_code=500
    )


@app.get("/api/health", summary="健康检查", tags=["系统"])
async def health_check():
    return JSONResponse(
        content={"status": "healthy", "service": "knowledge-graph-api"},
        status_code=200
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )