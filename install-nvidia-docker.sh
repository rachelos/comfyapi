#!/bin/bash
# NVIDIA Docker 2 安装脚本 (Linux)
# 适用于Ubuntu/Debian系统

set -e

echo -e "\e[32m开始安装 NVIDIA Container Toolkit (nvidia-docker2)...\e[0m"
echo -e "\e[36m注意: 此脚本使用NVIDIA官方源，请确保您的网络可以访问NVIDIA开发者网站\e[0m"

# 检查是否以root权限运行
if [ "$(id -u)" != "0" ]; then
   echo -e "\e[31m请以root权限运行此脚本!\e[0m"
   echo -e "\e[33m使用: sudo bash $0\e[0m"
   exit 1
fi

# 检查系统类型
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    echo -e "\e[31m无法确定操作系统类型!\e[0m"
    exit 1
fi

echo -e "\e[32m检测到系统: $OS $VER\e[0m"

# 检查Docker是否已安装
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "\e[32m检测到Docker: $DOCKER_VERSION\e[0m"
else
    echo -e "\e[31m未检测到Docker，正在安装...\e[0m"
    
    # 安装Docker
    # 使用国内镜像源
    cp /etc/apt/sources.list /etc/apt/sources.list.backup
    echo -e "\e[33m已备份原始sources.list到sources.list.backup\e[0m"
    
    # 替换为清华源（可根据实际情况选择其他国内源）
    sed -i 's|http://archive.ubuntu.com/ubuntu/|https://mirrors.tuna.tsinghua.edu.cn/ubuntu/|g' /etc/apt/sources.list
    sed -i 's|http://security.ubuntu.com/ubuntu/|https://mirrors.tuna.tsinghua.edu.cn/ubuntu/|g' /etc/apt/sources.list
    
    apt-get update
    apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
    
    # 创建密钥目录（如果不存在）
    mkdir -p /etc/apt/keyrings
    
    # 下载并安装Docker GPG密钥（使用国内镜像）
    curl -fsSL https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # 添加Docker仓库（使用国内镜像）
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/ubuntu $(lsb_release -cs) stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    systemctl enable docker
    systemctl start docker
    
    echo -e "\e[32mDocker安装完成\e[0m"
fi

# 检查NVIDIA驱动是否已安装
if command -v nvidia-smi &> /dev/null; then
    echo -e "\e[32m检测到NVIDIA驱动已安装\e[0m"
    nvidia-smi
else
    echo -e "\e[31m未检测到NVIDIA驱动，请先安装NVIDIA显卡驱动!\e[0m"
    echo -e "\e[33m可以使用以下命令安装:\e[0m"
    echo -e "\e[33mapt-get install -y ubuntu-drivers-common\e[0m"
    echo -e "\e[33mubuntu-drivers autoinstall\e[0m"
    exit 1
fi

# 安装NVIDIA Container Toolkit
echo -e "\e[36m正在安装NVIDIA Container Toolkit...\e[0m"

# 添加NVIDIA Container Toolkit的APT仓库
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
# 创建密钥目录（如果不存在）
mkdir -p /etc/apt/keyrings

# 下载并安装NVIDIA GPG密钥到新的位置（使用官方源）
curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/3bf863cc.pub | gpg --dearmor -o /etc/apt/keyrings/nvidia-docker.gpg

# 添加NVIDIA Docker仓库（使用官方源）
echo "deb [signed-by=/etc/apt/keyrings/nvidia-docker.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/ /" | \
  tee /etc/apt/sources.list.d/nvidia-docker.list

# 更新APT索引并安装nvidia-docker2
apt-get update
apt-get install -y nvidia-docker2

# 重启Docker服务
systemctl restart docker

echo -e "\e[32mNVIDIA Container Toolkit安装完成\e[0m"

# 测试NVIDIA Docker是否正常工作
echo -e "\e[36m正在测试NVIDIA Docker...\e[0m"

# 添加错误处理（使用官方镜像）
echo -e "\e[33m尝试拉取CUDA镜像...\e[0m"
docker pull nvidia/cuda:11.0-base || docker pull nvcr.io/nvidia/cuda:11.0-base

if ! docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi 2>/dev/null || \
   ! docker run --rm --gpus all nvcr.io/nvidia/cuda:11.0-base nvidia-smi; then
    echo -e "\e[31m测试失败! 请检查安装日志以获取更多信息\e[0m"
    echo -e "\e[33m可能需要重新启动系统后再尝试\e[0m"
    exit 1
fi

echo -e "\e[32m安装完成! 您现在可以在Docker容器中使用NVIDIA GPU了\e[0m"
echo -e "\e[36m您的docker-compose.yml文件已经包含了正确的GPU配置:\e[0m"
echo -e "deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]"

echo -e "\e[32m您可以使用 'docker-compose up' 启动您的ComfyUI服务\e[0m"