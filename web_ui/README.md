# ComfyUI JavaScript API

这是一个通用型的ComfyUI JavaScript客户端库，用于与ComfyUI后端API进行交互，支持图像生成、任务状态查询、结果获取等功能。

## 特性

- 命名空间封装，避免全局变量污染
- 支持自定义配置和回调函数
- 提供完整的错误处理机制
- 可在任何前端项目中集成使用
- 支持DOM操作和无DOM环境

## 快速开始

### 1. 引入API

```html
<script src="/ui/script.js"></script>
```

### 2. 初始化配置

```javascript
ComfyUI.init({
    apiBasePath: '/api',                           // API基础路径
    statusCheckInterval: 2000,                     // 状态检查间隔(毫秒)
    onStatusChange: (status, taskId, data) => {},  // 状态变更回调
    onProgress: (progress, data) => {},            // 进度更新回调
    onComplete: (imageUrl, promptId, taskId) => {}, // 完成回调
    onError: (error) => {}                         // 错误回调
});
```

### 3. 生成图像

```javascript
// 方式1: 使用表单数据(需要页面中有对应的表单元素)
await ComfyUI.generateImage();

// 方式2: 提供自定义参数
await ComfyUI.generateImage({
    prompt: "一只可爱的猫咪",
    negative_prompt: "模糊, 低质量",
    width: 512,
    height: 512,
    steps: 20,
    seed: -1
});
```

### 4. 检查任务状态

```javascript
// 检查当前任务
const status = await ComfyUI.checkTaskStatus();

// 检查指定任务
const status = await ComfyUI.checkTaskStatus("task_12345");
```

### 5. 取消任务

```javascript
const cancelled = await ComfyUI.cancelTask();
```

### 6. 获取任务结果

```javascript
const imageUrl = await ComfyUI.getTaskResult("prompt_12345");
```

## 完整API参考

### 初始化与配置

- `ComfyUI.init(config)` - 初始化API
- `ComfyUI.configure(config)` - 更新配置
- `ComfyUI.getConfig()` - 获取当前配置

### 任务管理

- `ComfyUI.generateImage(formData?)` - 生成图像
- `ComfyUI.checkTaskStatus(taskId?)` - 检查任务状态
- `ComfyUI.getTaskResult(promptId)` - 获取任务结果
- `ComfyUI.cancelTask()` - 取消当前任务
- `ComfyUI.getCurrentTaskId()` - 获取当前任务ID

## 集成示例

查看 `example-integration.html` 文件获取完整的集成示例。

## 无DOM环境使用

在没有DOM元素的环境中(如Node.js或纯API调用场景)，可以这样配置:

```javascript
ComfyUI.init({
    apiBasePath: '/api',
    getFormData: () => {
        // 返回自定义表单数据
        return {
            prompt: "自定义提示词",
            negative_prompt: "",
            width: 512,
            height: 512,
            steps: 20,
            seed: -1
        };
    }
});
```

## 注意事项

- API路径默认为`/api`，可通过配置修改
- 所有异步方法返回Promise，可使用async/await或then/catch处理
- 错误处理建议使用try/catch捕获异常