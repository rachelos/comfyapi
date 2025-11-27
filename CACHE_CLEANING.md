# 缓存清理功能说明

本项目提供了完整的缓存图片清理功能，可以自动或手动清理超过指定时间的缓存图片，有效管理存储空间。

## 功能特性

- ✅ 手动清理过期缓存
- ✅ 自动定期清理
- ✅ 试运行模式（预览将要删除的文件）
- ✅ 缓存统计信息显示
- ✅ 集成到图像生成流程中
- ✅ 定时调度器支持

## 缓存存储结构

```
resources/img/
├── 11/                    # 月份目录 (11月)
│   ├── task-id-1/        # 任务目录
│   │   ├── 0.png         # 生成的图片
│   │   ├── 1.png
│   │   └── images.json   # 图片信息
│   └── task-id-2/
└── 12/                    # 12月
    └── ...
```

## 使用方法

### 1. 手动清理缓存

#### 使用 ComfyUIClient

```python
from client.comfyui_client import ComfyUIClient

# 创建客户端
client = ComfyUIClient()

# 试运行（预览将要删除的文件）
client.clean_old_cache(days_threshold=1, dry_run=True)

# 实际清理
result = client.clean_old_cache(days_threshold=1, dry_run=False)
print(f"清理完成: {result}")
```

#### 使用独立清理工具

```python
from utils.cache_cleaner import clean_cache, show_cache_info

# 显示缓存信息
show_cache_info(days=1)

# 清理缓存
result = clean_cache(days=1, dry_run=False)
```

### 2. 自动清理

#### 集成到图像生成中

```python
from client.comfyui_client import ComfyUIClient

client = ComfyUIClient()

# 生成图像时会自动检查并清理过期缓存
prompt_id = client.generate_image(
    prompt="a beautiful landscape",
    width=512,
    height=512
)
```

#### 手动触发自动清理

```python
# 执行自动清理检查（基于时间间隔）
result = client.auto_clean_cache(days_threshold=1, check_interval_hours=24)
```

### 3. 定时调度器

#### 启动调度器

```bash
# 每天 02:00 自动清理
python scheduler.py --days 1 --time 02:00

# 立即执行一次清理
python scheduler.py --run-once --days 1

# 试运行模式
python scheduler.py --dry-run --days 1
```

#### 作为服务运行

```python
from scheduler import CacheScheduler

# 创建调度器
scheduler = CacheScheduler(clean_days=1, schedule_time="02:00")

# 启动调度器（会持续运行）
scheduler.start_scheduler()
```

## 命令行工具

### 独立清理工具

```bash
# 显示缓存信息
python utils/cache_cleaner.py --info --days 1

# 试运行清理
python utils/cache_cleaner.py --dry-run --days 1

# 实际清理
python utils/cache_cleaner.py --days 1
```

### 调度器工具

```bash
# 启动调度器
python scheduler.py --days 1 --time 02:00

# 立即执行一次
python scheduler.py --run-once --days 1

# 试运行
python scheduler.py --dry-run --days 1
```

### 示例脚本

```bash
# 运行各种示例
python clean_cache_example.py --example manual    # 手动清理示例
python clean_cache_example.py --example auto      # 自动清理示例
python clean_cache_example.py --example standalone # 独立工具示例
python clean_cache_example.py --example generate  # 生成时清理示例
```

## 配置参数

### 清理参数

- `days_threshold`: 清理阈值天数，默认为1天
- `dry_run`: 试运行模式，True时不实际删除文件
- `check_interval_hours`: 自动清理检查间隔，默认24小时

### 调度器参数

- `schedule_time`: 每天执行时间，格式为 "HH:MM"，默认 "02:00"
- `clean_days`: 清理超过指定天数的缓存

## API 参考

### ComfyUIClient 方法

#### `clean_old_cache(days_threshold=1, dry_run=False)`
清理超过指定天数的缓存文件

**参数:**
- `days_threshold`: 清理阈值天数
- `dry_run`: 是否为试运行模式

**返回:**
```python
{
    "deleted_files": 0,      # 删除的文件数
    "deleted_dirs": 0,       # 删除的目录数
    "freed_space": 0        # 释放的空间（字节）
}
```

#### `auto_clean_cache(days_threshold=1, check_interval_hours=24)`
自动清理缓存，基于时间间隔检查

**参数:**
- `days_threshold`: 清理阈值天数
- `check_interval_hours`: 检查间隔小时数

#### `get_cache_info(days_threshold=1)`
获取缓存统计信息

**返回:**
```python
{
    "total_size": 0,         # 总大小
    "total_dirs": 0,         # 总目录数
    "total_files": 0,        # 总文件数
    "old_dirs": 0,           # 过期目录数
    "old_files": 0,          # 过期文件数
    "old_size": 0            # 过期文件大小
}
```

### CacheCleaner 类

独立的缓存清理工具类，提供更灵活的清理控制。

## 日志记录

调度器和清理操作会记录到 `cache_cleaner.log` 文件中，包含：

- 清理任务执行时间
- 删除的文件和目录信息
- 释放的存储空间
- 错误信息

## 注意事项

1. **备份重要文件**: 清理前请确保没有重要的图片需要保留
2. **权限检查**: 确保程序有足够的权限删除缓存文件
3. **磁盘空间**: 清理大量文件时确保有足够的临时空间
4. **网络影响**: 如果图片正在被其他服务使用，清理可能影响功能

## 最佳实践

1. **定期清理**: 建议每天凌晨自动清理过期缓存
2. **监控空间**: 定期检查缓存大小，及时调整清理策略
3. **试运行**: 大规模清理前先使用试运行模式确认
4. **日志监控**: 关注清理日志，及时发现异常情况

## 故障排除

### 常见问题

**Q: 清理失败提示权限不足**
A: 检查程序对缓存目录的读写权限

**Q: 清理后缓存大小没有减少**
A: 检查是否有其他程序正在写入缓存，或确认清理阈值设置正确

**Q: 调度器停止工作**
A: 检查日志文件 `cache_cleaner.log` 查看错误信息

### 调试模式

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

启用调试日志可以查看更详细的执行信息。