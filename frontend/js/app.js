const API_BASE = '/api';
let meetingFiles = [];
let chatFiles = [];

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 3000);
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' bytes';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

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
            <span class="file-remove">×</span>
        `;
        
        const removeBtn = item.querySelector('.file-remove');
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            if (containerId === 'meetingFileName') {
                meetingFiles.splice(index, 1);
                document.getElementById('meetingText').textContent = meetingFiles.length > 0 ? `已选择 ${meetingFiles.length} 个会议文件` : '点击或拖拽上传会议记录';
            } else {
                chatFiles.splice(index, 1);
                document.getElementById('chatText').textContent = chatFiles.length > 0 ? `已选择 ${chatFiles.length} 个聊天文件` : '点击或拖拽上传聊天记录';
            }
            renderFileList(containerId, containerId === 'meetingFileName' ? meetingFiles : chatFiles);
        });
        
        container.appendChild(item);
    });
}

function handleFileSelect(input, type) {
    const files = Array.from(input.files);
    if (files.length === 0) return;

    const txtFiles = files.filter(f => f.name.endsWith('.txt'));
    if (txtFiles.length === 0) {
        showToast('请选择 .txt 格式文件', 'error');
        return;
    }

    if (type === 'meeting') {
        meetingFiles = [...meetingFiles, ...txtFiles];
        renderFileList('meetingFileName', meetingFiles);
        document.getElementById('meetingText').textContent = `已选择 ${meetingFiles.length} 个会议文件`;
    } else {
        chatFiles = [...chatFiles, ...txtFiles];
        renderFileList('chatFileName', chatFiles);
        document.getElementById('chatText').textContent = `已选择 ${chatFiles.length} 个聊天文件`;
    }

    input.value = '';
}

async function uploadFiles() {
    if (meetingFiles.length === 0 && chatFiles.length === 0) {
        showToast('请至少选择一个会议文件或聊天文件', 'error');
        return;
    }

    const uploadBtn = document.querySelector('button[onclick="uploadFiles()"]');
    const uploadBtnText = document.getElementById('uploadBtnText');
    const uploadLoading = document.getElementById('uploadLoading');

    uploadBtnText.style.display = 'none';
    uploadLoading.style.display = 'inline-block';
    uploadBtn.disabled = true;
    uploadBtn.classList.remove('btn-primary');
    uploadBtn.classList.add('btn-loading');

    try {
        const formData = new FormData();
        
        meetingFiles.forEach(file => {
            formData.append('meeting_files', file);
        });
        
        chatFiles.forEach(file => {
            formData.append('chat_files', file);
        });

        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        if (result.status === 'success') {
            showToast(result.message);
            uploadBtnText.textContent = '解析完成';
            uploadBtnText.style.display = 'inline-block';
            uploadLoading.style.display = 'none';
            uploadBtn.classList.remove('btn-loading');
            uploadBtn.classList.add('btn-success');

            document.getElementById('emptyState').style.display = 'none';
            document.getElementById('timeline').style.display = 'block';
            renderTimeline([]);
        } else {
            showToast(result.message || '上传失败', 'error');
            uploadBtnText.textContent = '上传并解析数据';
            uploadBtnText.style.display = 'inline-block';
            uploadLoading.style.display = 'none';
            uploadBtn.classList.remove('btn-loading');
            uploadBtn.classList.add('btn-primary');
        }
    } catch (error) {
        showToast('网络连接失败，请检查后端服务是否启动', 'error');
        uploadBtnText.textContent = '上传并解析数据';
        uploadBtnText.style.display = 'inline-block';
        uploadLoading.style.display = 'none';
        uploadBtn.classList.remove('btn-loading');
        uploadBtn.classList.add('btn-primary');
    } finally {
        uploadBtn.disabled = false;
    }
}

async function searchKnowledge() {
    const keyword = document.getElementById('searchInput').value.trim();
    if (!keyword) {
        showToast('请输入搜索关键词', 'error');
        return;
    }

    const searchBtn = document.querySelector('button[onclick="searchKnowledge()"]');
    const searchBtnText = document.getElementById('searchBtnText');
    const searchLoading = document.getElementById('searchLoading');

    searchBtnText.style.display = 'none';
    searchLoading.style.display = 'inline-block';
    searchBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/search?keyword=${encodeURIComponent(keyword)}`);

        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }

        const result = await response.json();

        if (result.status === 'success') {
            document.getElementById('emptyState').style.display = 'none';
            document.getElementById('timeline').style.display = 'block';
            renderTimeline(result.data);
            const decisionCount = result.data.decisions ? result.data.decisions.length : 0;
            const ruleCount = result.data.implicit_rules ? result.data.implicit_rules.length : 0;
            showToast(`搜索成功，找到 ${decisionCount} 条决策链，${ruleCount} 条隐形知识`, 'success');
        } else {
            showToast(result.message || '搜索失败', 'error');
        }
    } catch (error) {
        showToast('网络连接失败，请检查后端服务是否启动', 'error');
    } finally {
        searchBtnText.style.display = 'inline-block';
        searchLoading.style.display = 'none';
        searchBtn.disabled = false;
    }
}

async function analyzeEmployeeLoss() {
    const name = document.getElementById('lossInput').value.trim();
    if (!name) {
        showToast('请输入员工姓名', 'error');
        return;
    }

    const lossBtn = document.querySelector('button[onclick="analyzeEmployeeLoss()"]');
    const lossBtnText = document.getElementById('lossBtnText');
    const lossLoading = document.getElementById('lossLoading');

    lossBtnText.style.display = 'none';
    lossLoading.style.display = 'inline-block';
    lossBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/employee-loss?name=${encodeURIComponent(name)}`);

        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }

        const result = await response.json();

        if (result.status === 'success') {
            const data = result.data;

            document.getElementById('lossDecisions').textContent = data.decision_count;
            document.getElementById('lossTasks').textContent = data.task_count;
            document.getElementById('lossHours').textContent = data.estimated_reconstruction_hours;

            const progress = Math.min(data.estimated_reconstruction_hours * 5, 100);
            document.getElementById('lossProgress').style.width = progress + '%';

            let risk = '低';
            let color = '#28a745';
            if (data.estimated_reconstruction_hours > 20) { risk = '高'; color = '#dc3545'; }
            else if (data.estimated_reconstruction_hours > 8) { risk = '中'; color = '#ffc107'; }
            document.getElementById('lossRisk').textContent = risk;
            document.getElementById('lossRisk').style.color = color;

            document.getElementById('lossResult').style.display = 'block';

            showLossWarningToast(data.decision_count, data.estimated_reconstruction_hours);
        } else {
            showToast(result.message || '分析失败', 'error');
        }
    } catch (error) {
        showToast('网络连接失败，请检查后端服务是否启动', 'error');
    } finally {
        lossBtnText.style.display = 'inline-block';
        lossLoading.style.display = 'none';
        lossBtn.disabled = false;
    }
}

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

function renderTimeline(data) {
    const container = document.getElementById('timeline');
    container.innerHTML = '';

    const decisions = data.decisions || [];
    const implicit_rules = data.implicit_rules || [];

    if (decisions.length === 0 && implicit_rules.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:40px;color:#888;">暂无匹配数据，请尝试其他关键词</div>';
        return;
    }

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

['meetingUpload', 'chatUpload'].forEach(id => {
    const el = document.getElementById(id);
    el.addEventListener('dragover', e => { e.preventDefault(); el.classList.add('dragover'); });
    el.addEventListener('dragleave', e => { e.preventDefault(); el.classList.remove('dragover'); });
    el.addEventListener('drop', e => {
        e.preventDefault();
        el.classList.remove('dragover');
        const files = Array.from(e.dataTransfer.files);
        const txtFiles = files.filter(f => f.name.endsWith('.txt'));
        if (txtFiles.length === 0) {
            showToast('请上传 .txt 格式文件', 'error');
            return;
        }
        const type = id === 'meetingUpload' ? 'meeting' : 'chat';
        const input = document.getElementById(type + 'File');
        const dt = new DataTransfer();
        txtFiles.forEach(f => dt.items.add(f));
        input.files = dt.files;
        handleFileSelect(input, type);
    });
});
