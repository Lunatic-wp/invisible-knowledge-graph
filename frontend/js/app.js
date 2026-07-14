/**
 * 职场隐形知识图谱 - 前端逻辑
 * 
 * 主要功能：
 * 1. 文件上传管理：支持会议记录和聊天记录的多选上传与删除
 * 2. 知识检索：通过关键词搜索决策链和隐形知识
 * 3. 离职员工分析：分析员工掌握的核心知识，评估离职风险
 * 4. 可视化展示：渲染决策链和隐形知识的时间线视图
 * 
 * 技术栈：原生 JavaScript + HTML5 + CSS3
 * 
 * 文件结构：
 * - index.html          - 页面结构
 * - css/style.css       - 样式定义
 * - js/app.js           - 当前文件，前端逻辑
 * 
 * API 接口：
 * - POST /api/upload         - 上传文件并解析数据
 * - GET /api/search          - 关键词搜索
 * - GET /api/employee-loss   - 员工流失分析
 * - GET /api/health          - 健康检查
 * 
 * 注意事项：
 * - 文件上传仅支持 .txt 格式
 * - 支持拖拽上传和点击选择两种方式
 * - 删除文件时需阻止事件冒泡，避免触发文件选择弹窗
 */

/** API 基础路径 */
const API_BASE = '/api';

/** 会议文件列表（全局状态） */
let meetingFiles = [];

/** 聊天文件列表（全局状态） */
let chatFiles = [];

/**
 * 显示 Toast 消息提示
 * 
 * @param {string} message - 提示消息内容
 * @param {string} [type='success'] - 提示类型：success（成功）、error（错误）、warning（警告）
 * 
 * @example
 * showToast('操作成功', 'success');
 * showToast('文件上传失败', 'error');
 */
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 3000);
}

/**
 * 格式化文件大小
 * 
 * 将字节数转换为人类可读的格式（bytes/KB/MB）
 * 
 * @param {number} bytes - 文件字节数
 * @returns {string} 格式化后的文件大小字符串（如 "1.5 KB", "2.34 MB"）
 * 
 * @example
 * formatFileSize(1024)      // "1.0 KB"
 * formatFileSize(2048000)   // "1.95 MB"
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' bytes';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

/**
 * 渲染文件列表
 * 
 * 根据容器 ID 和文件列表动态生成文件项，包含文件名、大小和删除按钮
 * 
 * @param {string} containerId - 容器元素的 ID
 * @param {File[]} files - 文件对象数组
 * 
 * @note
 * 删除按钮绑定了点击事件，使用 e.stopPropagation() 和 e.preventDefault()
 * 阻止事件冒泡到上传区域，避免触发文件选择弹窗
 * 
 * @see handleFileSelect
 */
function renderFileList(containerId, files) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    files.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            <span class="file-icon">📄</span>
            <span class="file-name">${file.name}</span>
            <span class="file-size">${formatFileSize(file.size)}</span>
            <span class="file-remove" >×</span>
        `;
        
        // 绑定删除按钮事件（阻止事件冒泡，避免触发文件选择）
        const removeBtn = item.querySelector('.file-remove');
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            // 根据容器 ID 确定操作的文件列表
            if (containerId === 'meetingFileName') {
                meetingFiles.splice(index, 1);
                // 更新上传区域提示文本
                document.getElementById('meetingText').textContent = 
                    meetingFiles.length > 0 
                        ? `已选择 ${meetingFiles.length} 个会议文件` 
                        : '点击或拖拽上传会议记录';
            } else {
                chatFiles.splice(index, 1);
                // 更新上传区域提示文本
                document.getElementById('chatText').textContent = 
                    chatFiles.length > 0 
                        ? `已选择 ${chatFiles.length} 个聊天文件` 
                        : '点击或拖拽上传聊天记录';
            }
            // 重新渲染文件列表
            renderFileList(containerId, containerId === 'meetingFileName' ? meetingFiles : chatFiles);
        });
        
        container.appendChild(item);
    });
}

/**
 * 处理文件选择
 * 
 * 验证文件格式，更新全局文件列表，并重新渲染文件列表
 * 
 * @param {HTMLInputElement} input - 文件输入元素
 * @param {string} type - 文件类型：'meeting'（会议文件）或 'chat'（聊天文件）
 * 
 * @note
 * 处理完成后清空 input.value，允许重复选择同一文件
 */
function handleFileSelect(input, type) {
    const files = Array.from(input.files);
    if (files.length === 0) return;

    // 过滤非 .txt 文件
    const txtFiles = files.filter(f => f.name.endsWith('.txt'));
    if (txtFiles.length === 0) {
        showToast('请选择 .txt 格式文件', 'error');
        return;
    }

    // 更新全局文件列表并重新渲染
    if (type === 'meeting') {
        meetingFiles = [...meetingFiles, ...txtFiles];
        renderFileList('meetingFileName', meetingFiles);
        document.getElementById('meetingText').textContent = `已选择 ${meetingFiles.length} 个会议文件`;
    } else {
        chatFiles = [...chatFiles, ...txtFiles];
        renderFileList('chatFileName', chatFiles);
        document.getElementById('chatText').textContent = `已选择 ${chatFiles.length} 个聊天文件`;
    }

    // 清空 input 值，允许重复选择同一文件
    input.value = '';
}

/**
 * 上传文件并解析数据
 * 
 * 流程：
 * 1. 验证文件选择（至少选择一个文件）
 * 2. 显示加载状态（禁用按钮、显示加载动画）
 * 3. 构建 FormData（添加会议文件和聊天文件）
 * 4. 发送 POST 请求到 /api/upload
 * 5. 处理响应并更新 UI（显示成功/失败提示）
 * 6. 恢复按钮状态
 * 
 * @returns {Promise<void>}
 * 
 * @note
 * 使用 FormData 传递文件，支持多文件上传
 * 请求成功后自动显示时间线视图
 */
async function uploadFiles() {
    // 验证文件选择
    if (meetingFiles.length === 0 && chatFiles.length === 0) {
        showToast('请至少选择一个会议文件或聊天文件', 'error');
        return;
    }

    // 获取按钮元素（用于状态切换）
    const uploadBtn = document.querySelector('button[onclick="uploadFiles()"]');
    const uploadBtnText = document.getElementById('uploadBtnText');
    const uploadLoading = document.getElementById('uploadLoading');

    // 设置加载状态（禁用按钮、显示加载动画）
    uploadBtnText.style.display = 'none';
    uploadLoading.style.display = 'inline-block';
    uploadBtn.disabled = true;
    uploadBtn.classList.remove('btn-primary');
    uploadBtn.classList.add('btn-loading');

    try {
        // 构建 FormData，添加所有选中的文件
        const formData = new FormData();
        
        meetingFiles.forEach(file => {
            formData.append('meeting_files', file);
        });
        
        chatFiles.forEach(file => {
            formData.append('chat_files', file);
        });

        // 发送上传请求
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        if (result.status === 'success') {
            // 上传成功：显示成功提示，更新按钮状态
            showToast(result.message);
            uploadBtnText.textContent = '解析完成';
            uploadBtnText.style.display = 'inline-block';
            uploadLoading.style.display = 'none';
            uploadBtn.classList.remove('btn-loading');
            uploadBtn.classList.add('btn-success');

            // 显示时间线视图（隐藏空状态）
            document.getElementById('emptyState').style.display = 'none';
            document.getElementById('timeline').style.display = 'block';
            renderTimeline([]);
        } else {
            // 上传失败：显示错误提示，恢复按钮状态
            showToast(result.message || '上传失败', 'error');
            uploadBtnText.textContent = '上传并解析数据';
            uploadBtnText.style.display = 'inline-block';
            uploadLoading.style.display = 'none';
            uploadBtn.classList.remove('btn-loading');
            uploadBtn.classList.add('btn-primary');
        }
    } catch (error) {
        // 网络错误：显示错误提示，恢复按钮状态
        showToast('网络连接失败，请检查后端服务是否启动', 'error');
        uploadBtnText.textContent = '上传并解析数据';
        uploadBtnText.style.display = 'inline-block';
        uploadLoading.style.display = 'none';
        uploadBtn.classList.remove('btn-loading');
        uploadBtn.classList.add('btn-primary');
    } finally {
        // 恢复按钮可用状态
        uploadBtn.disabled = false;
    }
}

/**
 * 搜索知识
 * 
 * 根据关键词搜索决策链和隐形知识，渲染搜索结果
 * 
 * @returns {Promise<void>}
 * 
 * @note
 * 使用 encodeURIComponent 编码关键词，防止特殊字符导致请求失败
 * 请求成功后调用 renderTimeline 渲染搜索结果
 */
async function searchKnowledge() {
    const keyword = document.getElementById('searchInput').value.trim();
    if (!keyword) {
        showToast('请输入搜索关键词', 'error');
        return;
    }

    // 获取按钮元素（用于状态切换）
    const searchBtn = document.querySelector('button[onclick="searchKnowledge()"]');
    const searchBtnText = document.getElementById('searchBtnText');
    const searchLoading = document.getElementById('searchLoading');

    // 设置加载状态
    searchBtnText.style.display = 'none';
    searchLoading.style.display = 'inline-block';
    searchBtn.disabled = true;

    try {
        // 发送搜索请求（关键词进行 URI 编码）
        const response = await fetch(`${API_BASE}/search?keyword=${encodeURIComponent(keyword)}`);

        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }

        const result = await response.json();

        if (result.status === 'success') {
            // 搜索成功：显示时间线视图，渲染搜索结果
            document.getElementById('emptyState').style.display = 'none';
            document.getElementById('timeline').style.display = 'block';
            renderTimeline(result.data);
            
            // 显示搜索结果统计
            const decisionCount = result.data.decisions ? result.data.decisions.length : 0;
            const ruleCount = result.data.implicit_rules ? result.data.implicit_rules.length : 0;
            showToast(`搜索成功，找到 ${decisionCount} 条决策链，${ruleCount} 条隐形知识`, 'success');
        } else {
            // 搜索失败：显示错误提示
            showToast(result.message || '搜索失败', 'error');
        }
    } catch (error) {
        // 网络错误：显示错误提示
        showToast('网络连接失败，请检查后端服务是否启动', 'error');
    } finally {
        // 恢复按钮状态
        searchBtnText.style.display = 'inline-block';
        searchLoading.style.display = 'none';
        searchBtn.disabled = false;
    }
}

/**
 * 分析离职员工流失成本
 * 
 * 根据员工姓名查询其负责的任务和关联决策，评估离职风险
 * 
 * @returns {Promise<void>}
 * 
 * @note
 * 风险评估规则：
 * - 重建耗时 <= 8 小时：低风险（绿色）
 * - 8 小时 < 重建耗时 <= 20 小时：中风险（黄色）
 * - 重建耗时 > 20 小时：高风险（红色）
 */
async function analyzeEmployeeLoss() {
    const name = document.getElementById('lossInput').value.trim();
    if (!name) {
        showToast('请输入员工姓名', 'error');
        return;
    }

    // 获取按钮元素（用于状态切换）
    const lossBtn = document.querySelector('button[onclick="analyzeEmployeeLoss()"]');
    const lossBtnText = document.getElementById('lossBtnText');
    const lossLoading = document.getElementById('lossLoading');

    // 设置加载状态
    lossBtnText.style.display = 'none';
    lossLoading.style.display = 'inline-block';
    lossBtn.disabled = true;

    try {
        // 发送分析请求
        const response = await fetch(`${API_BASE}/employee-loss?name=${encodeURIComponent(name)}`);

        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }

        const result = await response.json();

        if (result.status === 'success') {
            const data = result.data;

            // 更新统计数据（关联决策数、任务数、重建耗时）
            document.getElementById('lossDecisions').textContent = data.decision_count;
            document.getElementById('lossTasks').textContent = data.task_count;
            document.getElementById('lossHours').textContent = data.estimated_reconstruction_hours;

            // 更新进度条（进度 = 重建小时数 * 5，最大100%）
            const progress = Math.min(data.estimated_reconstruction_hours * 5, 100);
            document.getElementById('lossProgress').style.width = progress + '%';

            // 更新风险等级和颜色
            let risk = '低';
            let color = '#28a745';
            if (data.estimated_reconstruction_hours > 20) { 
                risk = '高'; 
                color = '#dc3545'; 
            } else if (data.estimated_reconstruction_hours > 8) { 
                risk = '中'; 
                color = '#ffc107'; 
            }
            document.getElementById('lossRisk').textContent = risk;
            document.getElementById('lossRisk').style.color = color;

            // 显示结果面板
            document.getElementById('lossResult').style.display = 'block';

            // 显示离职风险警告 Toast
            showLossWarningToast(data.decision_count, data.estimated_reconstruction_hours);
        } else {
            // 分析失败：显示错误提示
            showToast(result.message || '分析失败', 'error');
        }
    } catch (error) {
        // 网络错误：显示错误提示
        showToast('网络连接失败，请检查后端服务是否启动', 'error');
    } finally {
        // 恢复按钮状态
        lossBtnText.style.display = 'inline-block';
        lossLoading.style.display = 'none';
        lossBtn.disabled = false;
    }
}

/**
 * 显示离职风险警告 Toast
 * 
 * 显示包含决策数量和重建耗时的详细警告信息
 * 
 * @param {number} decisionCount - 关联的决策数量
 * @param {number} hours - 预计重建耗时（小时）
 */
function showLossWarningToast(decisionCount, hours) {
    const toast = document.createElement('div');
    toast.className = 'toast toast-warning';
    toast.innerHTML = `
        <div style="display:flex;align-items:center;gap:12px;">
            <div style="font-size:24px;">⚠️</div>
            <div>
                <div style="font-weight:600;margin-bottom:4px;">离职风险警告</div>
                <div style="font-size:13px;">该员工掌握 <span style="color:#ffc107;font-weight:600;">${decisionCount}</span> 条核心决策链，新人重建预计需 <span style="color:#dc3545;font-weight:600;">${hours}</span> 小时！</div>
            </div>
        </div>
    `;
    document.body.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 5000);
}

/**
 * 渲染时间线视图
 * 
 * 根据搜索结果渲染决策链和隐形知识的时间线视图
 * 
 * @param {Object} data - 数据对象，包含：
 *                        - decisions: 决策链列表（可选）
 *                        - implicit_rules: 隐形知识列表（可选）
 * 
 * @note
 * 时间线视图结构：
 * 1. 决策链区域：显示决策节点及其关联的依据、任务、客户要求
 * 2. 隐形知识区域：显示经验规则和避坑警告
 * 
 * 如果数据为空，显示提示信息
 */
function renderTimeline(data) {
    const container = document.getElementById('timeline');
    container.innerHTML = '';

    const decisions = data.decisions || [];
    const implicit_rules = data.implicit_rules || [];

    // 空数据提示
    if (decisions.length === 0 && implicit_rules.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:40px;color:#888;">暂无匹配数据，请尝试其他关键词</div>';
        return;
    }

    // 渲染决策链区域
    if (decisions.length > 0) {
        const sectionHeader = document.createElement('div');
        sectionHeader.style.cssText = 'font-size:18px;font-weight:600;color:#007bff;margin-bottom:20px;display:flex;align-items:center;gap:10px;';
        sectionHeader.innerHTML = '<span>📊</span> 决策链';
        container.appendChild(sectionHeader);

        decisions.forEach((decision, index) => {
            const node = document.createElement('div');
            node.className = 'timeline-node';

            let html = `
                <div class="node-card">
                    <div class="node-header">
                        <span class="node-type type-decision">决策</span>
                        <span style="font-size:12px;color:#666;">决策 #${decision.id}</span>
                    </div>
                    <div class="node-content">${decision.content}</div>
                    <div class="node-meta">
                        <div class="meta-item">📅 会议ID: ${decision.meeting_id || '-'}</div>
                    </div>
            `;

            // 渲染依据节点（子节点）
            if (decision.evidences && decision.evidences.length > 0) {
                html += '<div class="sub-nodes">';
                decision.evidences.forEach(evidence => {
                    html += `
                        <div class="sub-node">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                                <span class="node-type type-evidence" style="font-size:10px;padding:2px 8px;">依据</span>
                                <span style="font-size:10px;color:#666;">来源: ${evidence.source_type}</span>
                            </div>
                            <div style="font-size:13px;color:#aaa;">${evidence.content}</div>
                        </div>
                    `;
                });
                html += '</div>';
            }

            // 渲染任务节点（子节点）
            if (decision.tasks && decision.tasks.length > 0) {
                html += '<div class="sub-nodes">';
                decision.tasks.forEach(task => {
                    html += `
                        <div class="sub-node">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                                <span class="node-type type-task" style="font-size:10px;padding:2px 8px;">任务</span>
                                <span style="font-size:10px;color:#666;">来源: ${task.source_type}</span>
                            </div>
                            <div style="font-size:13px;color:#aaa;margin-bottom:8px;">${task.content}</div>
                            <div style="display:flex;flex-wrap:wrap;gap:12px;font-size:11px;color:#666;">
                                ${task.deadline ? `<span>⏰ 截止: ${task.deadline}</span>` : ''}
                                ${task.assignee ? `<span>👤 负责人: ${task.assignee}</span>` : ''}
                            </div>
                    `;

                    // 渲染客户要求（任务的子节点）
                    if (task.clients && task.clients.length > 0) {
                        html += '<div style="margin-top:8px;padding-top:8px;border-top:1px solid #333;">';
                        task.clients.forEach(client => {
                            html += `
                                <div style="display:flex;align-items:center;gap:8px;margin-top:4px;">
                                    <span class="node-type type-client" style="font-size:9px;padding:1px 6px;">客户</span>
                                    <span style="font-size:12px;color:#ffc107;">${client.name}</span>
                                    <span style="font-size:11px;color:#888;">${client.requirement}</span>
                                </div>
                            `;
                        });
                        html += '</div>';
                    }

                    html += '</div>';
                });
                html += '</div>';
            }

            html += '</div>';
            node.innerHTML = html;
            container.appendChild(node);
        });
    }

    // 渲染隐形知识区域
    if (implicit_rules.length > 0) {
        const sectionHeader = document.createElement('div');
        sectionHeader.style.cssText = 'font-size:18px;font-weight:600;color:#ffc107;margin-bottom:20px;margin-top:40px;display:flex;align-items:center;gap:10px;';
        sectionHeader.innerHTML = '<span>💡</span> 职场隐形经验';
        container.appendChild(sectionHeader);

        implicit_rules.forEach((rule, index) => {
            const node = document.createElement('div');
            node.className = 'timeline-node';

            const typeLabel = rule.rule_type === 'warning' ? '避坑警告' : '经验规则';
            const typeClass = rule.rule_type === 'warning' ? 'type-warning' : 'type-rule';

            let html = `
                <div class="node-card">
                    <div class="node-header">
                        <span class="node-type ${typeClass}">${typeLabel}</span>
                        <span style="font-size:12px;color:#666;">#${rule.id}</span>
                    </div>
                    <div class="node-content">${rule.content}</div>
                    <div class="node-meta">
                        ${rule.author ? `<div class="meta-item">👤 ${rule.author}</div>` : ''}
                        ${rule.related_keywords ? `<div class="meta-item">🔖 ${rule.related_keywords}</div>` : ''}
                    </div>
                </div>
            `;

            node.innerHTML = html;
            container.appendChild(node);
        });
    }
}

/**
 * 初始化拖拽上传事件监听
 * 
 * 为会议文件和聊天文件的上传区域添加拖拽支持：
 * - dragover: 显示拖拽提示样式（高亮边框）
 * - dragleave: 移除拖拽提示样式
 * - drop: 处理文件拖拽上传
 * 
 * @note
 * 使用 DataTransfer API 设置 input 的 files 属性，
 * 然后调用 handleFileSelect 处理文件，保持逻辑统一
 */
['meetingUpload', 'chatUpload'].forEach(id => {
    const el = document.getElementById(id);
    el.addEventListener('dragover', e => { e.preventDefault(); el.classList.add('dragover'); });
    el.addEventListener('dragleave', e => { e.preventDefault(); el.classList.remove('dragover'); });
    el.addEventListener('drop', e => {
        e.preventDefault();
        el.classList.remove('dragover');
        
        // 获取拖拽的文件列表
        const files = Array.from(e.dataTransfer.files);
        
        // 过滤非 .txt 文件
        const txtFiles = files.filter(f => f.name.endsWith('.txt'));
        if (txtFiles.length === 0) {
            showToast('请上传 .txt 格式文件', 'error');
            return;
        }
        
        // 确定文件类型并处理
        const type = id === 'meetingUpload' ? 'meeting' : 'chat';
        const input = document.getElementById(type + 'File');
        
        // 使用 DataTransfer 设置 input 的 files 属性
        const dt = new DataTransfer();
        txtFiles.forEach(f => dt.items.add(f));
        input.files = dt.files;
        
        // 调用文件选择处理函数（复用逻辑）
        handleFileSelect(input, type);
    });
});
