/**
 * ComfyUI JavaScript API
 * 通用型图像生成客户端库
 * 版本: 1.0.0
 */

// ComfyUI 命名空间
const ComfyUI = (function() {
    // 私有变量
    let _currentTaskId = null;
    let _statusCheckInterval = null;
    let _config = {
        apiBasePath: '/api',
        statusCheckInterval: 2000,
        onStatusChange: null,
        onProgress: null,
        onComplete: null,
        onError: null
    };
    
    // DOM 元素引用
    let _elements = {
        generateBtn: null,
        statusDisplay: null,
        progressBar: null,
        resultImage: null,
        noImageText: null,
        imageInfoContent: null
    };
    
    // 初始化函数
    function init(config = {}) {
        // 合并配置
        _config = {..._config, ...config};
        console.log(_config)
        // 初始化DOM元素引用
        _elements = {
            generateBtn: document.getElementById('generate-btn'),
            statusDisplay: document.getElementById('status-display'),
            progressBar: document.getElementById('progress-bar'),
            resultImage: document.getElementById('result-image'),
            noImageText: document.getElementById('no-image-text'),
            imageInfoContent: document.getElementById('image-info-content')
        };
        
        // 绑定事件
        if (_elements.generateBtn) {
            _elements.generateBtn.addEventListener('click', startImageGeneration);
        }
        
        return this;
    }
    
    // 当DOM加载完成时自动初始化
    // document.addEventListener('DOMContentLoaded', () => {
    //     // 只有在没有手动初始化的情况下才自动初始化
    //     if (!ComfyUI.initialized) {
    //         ComfyUI.init();
    //     }
    // });

    // 开始图像生成流程
    async function startImageGeneration() {
        // 防止重复提交
        if (this._isGenerating) return;
        this._isGenerating = true;
        
        try {
            // 禁用按钮，防止重复提交
            setGeneratingState(true);
            
            // 获取表单数据
            const formData = getFormData();
            
            // 显示状态
            updateStatus('正在提交图像生成任务...');
            
            // 调用生成图像API
            const taskData = await generateImage(formData);
            
            if (taskData && taskData.task_id) {
                _currentTaskId = taskData.task_id;
                updateStatus(`任务已提交，ID: ${_currentTaskId}`);
                
                // 开始定时检查任务状态
                startStatusChecking();
                
                // 触发状态变更回调
                if (typeof _config.onStatusChange === 'function') {
                    _config.onStatusChange('submitted', _currentTaskId);
                }
                
                return _currentTaskId;
            } else {
                throw new Error('未能获取有效的任务ID');
            }
        } catch (error) {
            console.error('图像生成失败:', error);
            updateStatus(`错误: ${error.message}`);
            setGeneratingState(false);
            this._isGenerating = false;
            
            // 触发错误回调
            if (typeof _config.onError === 'function') {
                _config.onError(error);
            }
            
            throw error;
        } finally {
            this._isGenerating = false;
        }
    }

    // 获取表单数据
    function getFormData() {
        // 如果提供了自定义表单数据获取函数，则使用它
        if (typeof _config.getFormData === 'function') {
            return _config.getFormData();
        }
        
        // 默认从DOM获取数据
        return {
            prompt: document.getElementById('prompt')?.value.trim() || '',
            workflow: document.getElementById('workflow')?.value.trim() || '',
            negative_prompt: document.getElementById('negative-prompt')?.value.trim() || '',
            width: parseInt(document.getElementById('width')?.value || '512'),
            height: parseInt(document.getElementById('height')?.value || '512'),
            batch_size: parseInt(document.getElementById('batch_size')?.value || '2'),
        };
    }

    // 调用生成图像API
    async function generateImage(data) {
        const apiUrl = `${_config.apiBasePath}/generate_image`;
        
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API错误 (${response.status}): ${errorText}`);
        }
        
        return await response.json();
    }

    // 开始定时检查任务状态
    function startStatusChecking() {
        // 清除可能存在的旧定时器
        if (_statusCheckInterval) {
            clearInterval(_statusCheckInterval);
        }
        
        // 设置进度条初始状态
        updateProgressBar(0);
        
        // 按配置的间隔检查任务状态
        _statusCheckInterval = setInterval(checkTaskStatus, _config.statusCheckInterval);
    }

    // 检查任务状态
    async function checkTaskStatus() {
        if (!_currentTaskId) return;
        
        try {
            const apiUrl = `${_config.apiBasePath}/task_status/${_currentTaskId}`;
            const response = await fetch(apiUrl);
            
            if (!response.ok) {
                throw new Error(`获取任务状态失败 (${response.status})`);
            }
            
            const statusData = await response.json();
            
            // 更新UI显示状态
            handleTaskStatus(statusData);
            
            return statusData;
        } catch (error) {
            console.error('检查任务状态失败:', error);
            updateStatus(`检查状态错误: ${error.message}`);
            
            // 触发错误回调
            if (typeof _config.onError === 'function') {
                _config.onError(error);
            }
            
            throw error;
        }
    }

    // 处理任务状态
    function handleTaskStatus(statusData) {
        // 更新状态显示
        updateStatus(`状态: ${getStatusText(statusData.status)}`);
        
        // 如果有进度信息，更新进度条
        if (statusData.progress !== undefined) {
            updateProgressBar(statusData.progress);
            
            // 触发进度回调
            if (typeof _config.onProgress === 'function') {
                _config.onProgress(statusData.progress, statusData);
            }
        }
        
        // 触发状态变更回调
        if (typeof _config.onStatusChange === 'function') {
            _config.onStatusChange(statusData.status, _currentTaskId, statusData);
        }
        
        // 如果任务完成，获取结果
        if (statusData.status === 'completed') {
            clearInterval(_statusCheckInterval);
            getTaskResult(statusData.task_id);
        }
        
        // 如果任务失败，停止检查
        if (statusData.status === 'failed') {
            clearInterval(_statusCheckInterval);
            updateStatus(`任务失败: ${statusData.error || '未知错误'}`);
            setGeneratingState(false);
            
            // 触发错误回调
            if (typeof _config.onError === 'function') {
                _config.onError(new Error(statusData.error || '未知错误'), statusData);
            }
        }
    }

    // 获取状态文本
    function getStatusText(status) {
        const statusMap = {
            'pending': '等待中',
            'processing': '处理中',
            'completed': '已完成',
            'failed': '失败'
        };
        
        return statusMap[status] || status;
    }

    // 更新进度条
    function updateProgressBar(progress) {
        // 确保进度在0-100之间
        const percentage = Math.min(100, Math.max(0, progress));
        
        if (_elements.progressBar) {
            _elements.progressBar.style.width = `${percentage}%`;
        }
    }

    // 获取任务结果
    async function getTaskResult(promptId) {
        try {
            updateStatus('正在获取生成的图像...');
            
            // 获取图像URL列表
            const apiUrl = `${_config.apiBasePath}/get_file/${promptId}`;
            const response = await fetch(apiUrl);
            
            if (!response.ok) {
                throw new Error(`获取图像列表失败 (${response.status})`);
            }
            
            const data = await response.json();
            const imageData = data?.file_path || [];
            const imageUrls = Array.isArray(imageData) ? imageData : [imageData];
            
            // 循环显示所有图像
            for (let i = 0; i < imageUrls.length; i++) {
                const imageUrl = imageUrls[i];
                displayImage(imageUrl, `${promptId}_${i}`);
                
                // 更新状态显示当前进度
                updateStatus(`显示图像 ${i + 1}/${imageUrls.length}`);
                
                // 如果不是最后一张图片，等待一小段时间再显示下一张
                if (i < imageUrls.length - 1) {
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
            }
            
            // 重置状态
            setGeneratingState(false);
            updateStatus(`图像生成完成！共 ${imageUrls.length} 张图像`);
            
            // 触发完成回调
            if (typeof _config.onComplete === 'function') {
                _config.onComplete(imageUrls, promptId, _currentTaskId);
            }
            
            return imageUrls;
        } catch (error) {
            console.error('获取任务结果失败:', error);
            updateStatus(`获取结果错误: ${error.message}`);
            setGeneratingState(false);
            
            // 触发错误回调
            if (typeof _config.onError === 'function') {
                _config.onError(error);
            }
            
            throw error;
        }
    }

    // 显示图像
    function displayImage(imageUrl, promptId) {
        // 如果没有DOM元素，只返回URL
        if (!_elements.resultImage || !_elements.noImageText) {
            return imageUrl;
        }
        
        // 检查是否需要创建图像容器
        let imageContainer = document.getElementById('image-container');
        if (!imageContainer) {
            // 创建图像容器
            imageContainer = document.createElement('div');
            imageContainer.id = 'image-container';
            imageContainer.style.display = 'flex';
            imageContainer.style.flexWrap = 'wrap';
            imageContainer.style.gap = '10px';
            imageContainer.style.justifyContent = 'center';
            
            // 将容器插入到结果图像的位置
            _elements.resultImage.parentNode.insertBefore(imageContainer, _elements.resultImage);
            
            // 隐藏原始图像元素
            _elements.resultImage.style.display = 'none';
        }
        
        // 隐藏提示文本
        _elements.noImageText.style.display = 'none';
        
        // 创建新的图像元素
        const imgElement = document.createElement('img');
        imgElement.src = imageUrl;
        imgElement.alt = `生成图像 ${promptId}`;
        imgElement.style.maxWidth = '100%';
        imgElement.style.height = 'auto';
        imgElement.style.margin = '5px';
        imgElement.style.border = '1px solid #ddd';
        imgElement.style.borderRadius = '4px';
        imgElement.dataset.promptId = promptId;
        
        // 添加图像加载错误处理
        imgElement.onerror = () => {
            imgElement.style.display = 'none';
            const errorMsg = document.createElement('div');
            errorMsg.textContent = '图像加载失败';
            errorMsg.style.color = 'red';
            errorMsg.style.padding = '10px';
            imageContainer.appendChild(errorMsg);
            
            // 触发错误回调
            if (typeof _config.onError === 'function') {
                _config.onError(new Error(`图像 ${promptId} 加载失败`));
            }
        };
        
        // 将图像添加到容器中
        imageContainer.appendChild(imgElement);
        
        // 显示图像信息
        if (_elements.imageInfoContent) {
            const timestamp = new Date().toLocaleString();
            const currentInfo = _elements.imageInfoContent.textContent;
            _elements.imageInfoContent.textContent = `${currentInfo ? currentInfo + '\n\n' : ''}图像 ${promptId}:\n生成时间: ${timestamp}\n任务ID: ${_currentTaskId||""}`;
        }
        
        return imageUrl;
    }

    // 更新状态显示
    function updateStatus(message) {
        if (_elements.statusDisplay) {
            _elements.statusDisplay.textContent = message;
        }
        
        return message;
    }
    
    // 设置生成状态
    function setGeneratingState(isGenerating) {
        if (_elements.generateBtn) {
            _elements.generateBtn.disabled = isGenerating;
            _elements.generateBtn.textContent = isGenerating ? '生成中...' : '生成图像';
        }
    }
    
    // 公共API
    return {
        // 属性
        initialized: false,
        version: '1.0.0',
        
        // 初始化方法
        init: function(config) {
            init(config);
            this.initialized = true;
            return this;
        },
        
        // 配置方法
        configure: function(config) {
            _config = {..._config, ...config};
            console.log(config)
            return this;
        },
        
        // 获取当前配置
        getConfig: function() {
            return {..._config};
        },
        
        // 生成图像
        generateImage: async function(formData) {
            if (formData) {
                // 使用提供的表单数据
                return await generateImage(formData);
            } else {
                // 使用默认流程
                return await startImageGeneration();
            }
        },
        
        // 检查任务状态
        checkTaskStatus: async function(taskId) {
            // 如果提供了任务ID，临时设置为当前任务
            const originalTaskId = _currentTaskId;
            if (taskId) {
                _currentTaskId = taskId;
            }
            
            try {
                const result = await checkTaskStatus();
                
                // 恢复原始任务ID
                if (taskId) {
                    _currentTaskId = originalTaskId;
                }
                
                return result;
            } catch (error) {
                // 恢复原始任务ID
                if (taskId) {
                    _currentTaskId = originalTaskId;
                }
                throw error;
            }
        },
        
        // 获取任务结果
        getTaskResult: async function(promptId) {
            return await getTaskResult(promptId);
        },
        
        // 取消当前任务
        cancelTask: async function() {
            if (!_currentTaskId) return false;
            
            try {
                const apiUrl = `${_config.apiBasePath}/cancel_task/${_currentTaskId}`;
                const response = await fetch(apiUrl, {
                    method: 'POST'
                });
                
                if (!response.ok) {
                    throw new Error(`取消任务失败 (${response.status})`);
                }
                
                clearInterval(_statusCheckInterval);
                updateStatus('任务已取消');
                setGeneratingState(false);
                
                return true;
            } catch (error) {
                console.error('取消任务失败:', error);
                return false;
            }
        },
        
        // 获取当前任务ID
        getCurrentTaskId: function() {
            return _currentTaskId;
        }
    };
})();