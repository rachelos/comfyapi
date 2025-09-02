# NVIDIA Docker 安装指南

本目录包含两个安装脚本，用于在不同操作系统上安装NVIDIA Container Toolkit (nvidia-docker2)，以便Docker容器能够使用GPU资源。

## Windows 环境安装

1. 确保已安装最新的NVIDIA显卡驱动
2. 安装Docker Desktop for Windows
3. 以管理员身份运行PowerShell
4. 执行以下命令：

```powershell
.\install-nvidia-docker.ps1
```

5. 按照提示重启Docker Desktop
6. 测试安装是否成功：

```powershell
docker run --gpus all nvidia/cuda:11.0-base nvidia-smi
```

## Linux 环境安装

1. 确保已安装最新的NVIDIA显卡驱动
2. 执行以下命令：

```bash
cd /path/to/comfyapi
sudo bash ./install-nvidia-docker.sh
```

3. 脚本会自动安装Docker（如果尚未安装）和NVIDIA Container Toolkit
4. 安装完成后会自动测试GPU是否可用

## 启动ComfyUI

安装完成后，您可以使用以下命令启动ComfyUI：

```bash
docker-compose up -d
```

ComfyUI将在 http://localhost:8188 上可用。

## 注意事项

- 您的`compose.yml`文件已经包含了正确的GPU配置
- 如果您需要指定特定的GPU，可以修改`compose.yml`文件中的`device_ids`部分
- 确保您的NVIDIA驱动版本与CUDA版本兼容

## 故障排除

如果遇到问题，请检查：

1. NVIDIA驱动是否正确安装（使用`nvidia-smi`命令验证）
2. Docker是否正确配置（检查daemon.json文件）
3. 在Windows上，确保已启用WSL 2和虚拟化功能