#!/bin/bash

# NVIDIA Tesla V100 SXM2 32GB 驱动自动安装脚本
# 作者: Craft
# 创建日期: 2025/09/01

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 打印带颜色的信息函数
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否以root权限运行
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        print_error "此脚本需要root权限运行"
        print_info "请使用 'sudo bash $0' 重新运行此脚本"
        exit 1
    fi
}

# 检查系统是否为Linux
check_system() {
    if [ "$(uname)" != "Linux" ]; then
        print_error "此脚本仅适用于Linux系统"
        exit 1
    fi
    
    print_info "检测到Linux系统: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
}

# 检查是否有NVIDIA Tesla V100 GPU
check_gpu() {
    if ! command -v lspci &> /dev/null; then
        print_info "安装pciutils以检测GPU..."
        if command -v apt &> /dev/null; then
            apt update && apt install -y pciutils
        elif command -v yum &> /dev/null; then
            yum install -y pciutils
        else
            print_error "无法安装pciutils，请手动安装后重试"
            exit 1
        fi
    fi
    
    if lspci | grep -i "NVIDIA" | grep -i "V100" &> /dev/null; then
        print_success "检测到NVIDIA Tesla V100 GPU"
    else
        print_warning "未检测到NVIDIA Tesla V100 GPU，但仍将继续安装驱动"
        print_info "GPU信息: $(lspci | grep -i "NVIDIA" || echo "未检测到NVIDIA GPU")"
    fi
}

# 安装依赖
install_dependencies() {
    print_info "安装必要的依赖..."
    
    if command -v apt &> /dev/null; then
        # Debian/Ubuntu系统
        apt update
        apt install -y build-essential dkms linux-headers-$(uname -r) gcc make
    elif command -v yum &> /dev/null; then
        # RHEL/CentOS系统
        yum groupinstall -y "Development Tools"
        yum install -y kernel-devel-$(uname -r) kernel-headers-$(uname -r) gcc make dkms
    else
        print_error "不支持的Linux发行版，请手动安装必要的依赖"
        print_info "需要的依赖: gcc, make, kernel-headers, kernel-devel, dkms"
        exit 1
    fi
    
    print_success "依赖安装完成"
}

# 禁用nouveau驱动
disable_nouveau() {
    print_info "检查并禁用nouveau驱动..."
    
    if lsmod | grep -i nouveau &> /dev/null; then
        print_info "检测到nouveau驱动正在运行，准备禁用..."
        
        # 创建blacklist文件
        cat > /etc/modprobe.d/blacklist-nouveau.conf << EOF
blacklist nouveau
options nouveau modeset=0
EOF
        
        # 更新initramfs
        if command -v update-initramfs &> /dev/null; then
            update-initramfs -u
        elif [ -f /boot/initramfs-$(uname -r).img ]; then
            dracut -f /boot/initramfs-$(uname -r).img $(uname -r)
        else
            print_warning "无法更新initramfs，可能需要手动重建"
        fi
        
        print_warning "需要重启系统以完全禁用nouveau驱动"
        read -p "是否立即重启系统? (y/n): " choice
        if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
            print_info "系统将在5秒后重启..."
            sleep 5
            reboot
            exit 0
        else
            print_warning "请在安装完成后手动重启系统，否则驱动可能无法正常工作"
        fi
    else
        print_success "nouveau驱动未运行或已被禁用"
    fi
}

# 使用ubuntu-drivers安装NVIDIA驱动
install_driver_ubuntu() {
    print_info "使用Ubuntu系统工具安装NVIDIA驱动..."
    
    # 检查是否为Ubuntu系统
    if [ ! -f /etc/lsb-release ] || ! grep -q "Ubuntu" /etc/lsb-release; then
        print_error "当前系统不是Ubuntu，无法使用ubuntu-drivers工具"
        print_info "请选择其他安装方式"
        install_driver_manual
        return
    fi
    
    # 检查ubuntu-drivers命令是否可用
    if ! command -v ubuntu-drivers &> /dev/null; then
        print_info "安装ubuntu-drivers-common包..."
        apt update
        apt install -y ubuntu-drivers-common
    fi
    
    # 添加NVIDIA PPA仓库以获取最新驱动
    print_info "添加NVIDIA驱动PPA仓库..."
    if ! command -v add-apt-repository &> /dev/null; then
        apt install -y software-properties-common
    fi
    
    # 添加图形驱动PPA
    add-apt-repository -y ppa:graphics-drivers/ppa
    apt update
    
    # 显示可用的NVIDIA驱动
    print_info "检测可用的NVIDIA驱动..."
    ubuntu-drivers devices
    
    # 提供安装选项
    echo ""
    echo "安装选项："
    echo "1. 自动安装推荐驱动（推荐）"
    echo "2. 安装特定版本驱动"
    echo "3. 手动安装（使用.run文件）"
    read -p "请选择安装方式 [1-3]: " install_choice
    
    case $install_choice in
        1)
            # 自动安装推荐驱动
            print_info "安装NVIDIA推荐驱动..."
            ubuntu-drivers autoinstall
            
            # 检查安装结果
            if [ $? -eq 0 ]; then
                print_success "NVIDIA驱动安装成功!"
            else
                print_error "NVIDIA驱动安装失败"
                exit 1
            fi
            ;;
            
        2)
            # 安装特定版本驱动
            print_info "可用的NVIDIA驱动版本:"
            apt search nvidia-driver | grep "nvidia-driver-[0-9]" | cut -d'/' -f1
            
            read -p "请输入要安装的驱动版本（例如: nvidia-driver-535）: " driver_package
            
            print_info "安装 $driver_package..."
            apt install -y $driver_package
            
            # 检查安装结果
            if [ $? -eq 0 ]; then
                print_success "NVIDIA驱动 $driver_package 安装成功!"
            else
                print_error "NVIDIA驱动安装失败"
                exit 1
            fi
            ;;
            
        3)
            # 手动安装
            install_driver_manual
            ;;
            
        *)
            print_error "无效的选择"
            exit 1
            ;;
    esac
}

# 手动下载和安装NVIDIA驱动（备选方法）
install_driver_manual() {
    print_info "准备手动安装NVIDIA Tesla V100驱动..."
    
    # 创建临时目录
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    # 提供获取驱动的方式
    print_info "NVIDIA驱动获取方式："
    echo "1. 尝试自动下载（可能受网络限制）"
    echo "2. 手动下载指导（推荐）"
    echo "3. 使用本地已下载的驱动文件"
    read -p "请选择获取方式 [1-3]: " download_choice
    
    case $download_choice in
        1)
            # 自动下载尝试
            print_info "尝试自动下载NVIDIA驱动..."
            
            # 首选驱动版本列表 - 这些是已知适用于Tesla V100的稳定版本
            DRIVER_VERSIONS=("535.183.01" "535.154.05" "535.129.03" "525.147.05" "525.125.06")
            DRIVER_URL=""
            
            # 尝试不同的下载镜像和版本
            MIRRORS=(
                "https://developer.download.nvidia.com/compute/cuda/redist"
                "https://developer.download.nvidia.com/compute/driver/redist"
                "https://developer.nvidia.com/downloads"
                "https://international.download.nvidia.com/tesla"
            )
            
            print_info "尝试查找可用的驱动下载链接..."
            
            for VERSION in "${DRIVER_VERSIONS[@]}"; do
                for MIRROR in "${MIRRORS[@]}"; do
                    TEST_URL="${MIRROR}/${VERSION}/NVIDIA-Linux-x86_64-${VERSION}.run"
                    print_info "尝试: ${TEST_URL}"
                    
                    # 使用curl或wget测试URL是否可访问
                    if command -v curl &> /dev/null; then
                        if curl --output /dev/null --silent --head --fail "$TEST_URL"; then
                            DRIVER_URL="$TEST_URL"
                            DRIVER_VERSION="$VERSION"
                            break 2
                        fi
                    elif command -v wget &> /dev/null; then
                        if wget --spider "$TEST_URL" 2>/dev/null; then
                            DRIVER_URL="$TEST_URL"
                            DRIVER_VERSION="$VERSION"
                            break 2
                        fi
                    fi
                done
            done
            
            if [ -z "$DRIVER_URL" ]; then
                print_warning "自动下载失败，切换到手动下载模式..."
                download_choice=2
            else
                print_info "找到可用下载链接: ${DRIVER_URL}"
                print_info "下载NVIDIA驱动版本: ${DRIVER_VERSION}"
                
                if command -v wget &> /dev/null; then
                    wget "$DRIVER_URL" -O nvidia-driver.run
                elif command -v curl &> /dev/null; then
                    curl -L "$DRIVER_URL" -o nvidia-driver.run
                fi
                
                if [ ! -f nvidia-driver.run ]; then
                    print_error "驱动下载失败，切换到手动下载模式..."
                    download_choice=2
                else
                    chmod +x nvidia-driver.run
                    print_success "驱动下载完成: $(pwd)/nvidia-driver.run"
                fi
            fi
            ;;
        
        2)
            # 手动下载指导
            print_info "请按照以下步骤手动下载NVIDIA Tesla V100驱动:"
            echo ""
            echo "1. 访问NVIDIA驱动下载页面: https://www.nvidia.com/Download/index.aspx"
            echo "2. 选择以下选项:"
            echo "   - 产品类型: Tesla"
            echo "   - 产品系列: V-Series"
            echo "   - 产品: Tesla V100"
            echo "   - 操作系统: Linux 64-bit"
            echo "   - CUDA Toolkit: 选择您需要的版本（如不确定，选择最新版本）"
            echo "3. 点击搜索，在结果页面下载驱动程序"
            echo "4. 或者直接访问NVIDIA数据中心驱动页面: https://www.nvidia.com/Download/driverResults.aspx/198666/en-us/"
            echo ""
            echo "另外，您也可以通过CUDA Toolkit下载获取驱动:"
            echo "访问: https://developer.nvidia.com/cuda-downloads"
            echo ""
            
            read -p "驱动下载完成后，请输入驱动文件的完整路径: " driver_path
            
            if [ -f "$driver_path" ]; then
                cp "$driver_path" nvidia-driver.run
                chmod +x nvidia-driver.run
                print_success "已使用指定的驱动文件: $driver_path"
                DRIVER_VERSION=$(echo "$driver_path" | grep -oP '(?<=NVIDIA-Linux-x86_64-)[0-9.]+(?=\.run)' || echo "未知版本")
                print_info "驱动版本: ${DRIVER_VERSION}"
            else
                print_error "指定的文件不存在: $driver_path"
                exit 1
            fi
            ;;
            
        3)
            # 使用本地文件
            read -p "请输入本地NVIDIA驱动文件的完整路径: " local_driver
            
            if [ -f "$local_driver" ]; then
                cp "$local_driver" nvidia-driver.run
                chmod +x nvidia-driver.run
                print_success "已使用本地驱动文件: $local_driver"
                DRIVER_VERSION=$(echo "$local_driver" | grep -oP '(?<=NVIDIA-Linux-x86_64-)[0-9.]+(?=\.run)' || echo "未知版本")
                print_info "驱动版本: ${DRIVER_VERSION}"
            else
                print_error "指定的文件不存在: $local_driver"
                exit 1
            fi
            ;;
            
        *)
            print_error "无效的选择"
            exit 1
            ;;
    esac
    
    # 安装下载的驱动
    print_info "开始安装NVIDIA驱动..."
    
    # 停止X服务器（如果正在运行）
    if systemctl is-active gdm &> /dev/null || systemctl is-active lightdm &> /dev/null; then
        print_info "检测到X服务器正在运行，尝试停止..."
        systemctl isolate multi-user.target
    fi
    
    # 安装选项
    INSTALL_OPTIONS="--silent --dkms --no-opengl-files --no-nouveau-check"
    
    print_info "执行安装命令: ./nvidia-driver.run $INSTALL_OPTIONS"
    ./nvidia-driver.run $INSTALL_OPTIONS
    
    INSTALL_STATUS=$?
    if [ $INSTALL_STATUS -eq 0 ]; then
        print_success "NVIDIA驱动安装成功!"
    else
        print_error "NVIDIA驱动安装失败，退出代码: $INSTALL_STATUS"
        print_info "请查看日志文件获取详细信息: /var/log/nvidia-installer.log"
        exit 1
    fi
}

# 验证安装
verify_installation() {
    print_info "验证NVIDIA驱动安装..."
    
    # 加载NVIDIA驱动模块
    modprobe nvidia
    
    if [ $? -ne 0 ]; then
        print_error "无法加载NVIDIA驱动模块"
        exit 1
    fi
    
    # 检查nvidia-smi是否可用
    if command -v nvidia-smi &> /dev/null; then
        print_success "NVIDIA驱动安装验证成功"
        print_info "GPU信息:"
        nvidia-smi
    else
        print_error "NVIDIA驱动安装验证失败，未找到nvidia-smi命令"
        exit 1
    fi
}

# 清理未使用的NVIDIA驱动
clean_unused_drivers() {
    print_info "检查并清理未使用的NVIDIA驱动..."
    
    # 检查是否为Ubuntu系统
    if [ -f /etc/lsb-release ] && grep -q "Ubuntu" /etc/lsb-release; then
        # 获取当前正在使用的驱动版本
        CURRENT_DRIVER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null || echo "未知")
        
        if [ "$CURRENT_DRIVER" != "未知" ]; then
            print_info "当前正在使用的NVIDIA驱动版本: $CURRENT_DRIVER"
            
            # 列出所有已安装的NVIDIA驱动包
            print_info "已安装的NVIDIA驱动包:"
            INSTALLED_DRIVERS=$(dpkg -l | grep -E 'nvidia-driver-[0-9]+' | awk '{print $2}')
            
            if [ -n "$INSTALLED_DRIVERS" ]; then
                echo "$INSTALLED_DRIVERS"
                
                # 询问是否清理旧驱动
                echo ""
                read -p "是否清理未使用的NVIDIA驱动? (y/n): " clean_choice
                
                if [ "$clean_choice" = "y" ] || [ "$clean_choice" = "Y" ]; then
                    print_info "清理未使用的NVIDIA驱动包..."
                    
                    # 获取当前使用的驱动包名称
                    CURRENT_PACKAGE=$(dpkg -l | grep -E "nvidia-driver-[0-9]+" | grep "$CURRENT_DRIVER" | awk '{print $2}' || echo "")
                    
                    # 如果找不到精确匹配，尝试模糊匹配
                    if [ -z "$CURRENT_PACKAGE" ]; then
                        CURRENT_VERSION=$(echo "$CURRENT_DRIVER" | cut -d. -f1)
                        CURRENT_PACKAGE=$(dpkg -l | grep -E "nvidia-driver-$CURRENT_VERSION" | awk '{print $2}' || echo "")
                    fi
                    
                    if [ -n "$CURRENT_PACKAGE" ]; then
                        print_info "保留当前使用的驱动包: $CURRENT_PACKAGE"
                        
                        # 移除其他NVIDIA驱动包
                        for DRIVER_PKG in $INSTALLED_DRIVERS; do
                            if [ "$DRIVER_PKG" != "$CURRENT_PACKAGE" ]; then
                                print_info "移除未使用的驱动包: $DRIVER_PKG"
                                apt purge -y $DRIVER_PKG
                            fi
                        done
                        
                        # 清理不再需要的依赖
                        apt autoremove -y
                        
                        print_success "未使用的NVIDIA驱动已清理完成"
                    else
                        print_warning "无法确定当前使用的驱动包，跳过清理"
                    fi
                else
                    print_info "跳过驱动清理"
                fi
            else
                print_info "未检测到多个NVIDIA驱动包，无需清理"
            fi
        else
            print_warning "无法获取当前驱动版本，跳过清理"
        fi
    else
        print_info "非Ubuntu系统，跳过驱动清理"
    fi
}

# 安装CUDA工具包（可选）
install_cuda() {
    print_info "是否安装CUDA工具包? (推荐用于深度学习和科学计算)"
    read -p "安装CUDA工具包? (y/n): " choice
    
    if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
        print_info "准备安装CUDA工具包..."
        
        # 这里可以添加CUDA安装逻辑
        print_info "CUDA安装功能尚未实现，请参考NVIDIA官方文档手动安装CUDA"
        print_info "CUDA下载页面: https://developer.nvidia.com/cuda-downloads"
    else
        print_info "跳过CUDA工具包安装"
    fi
}

# 清理临时文件
cleanup() {
    print_info "清理临时文件..."
    cd /
    rm -rf "$TEMP_DIR"
    print_success "临时文件清理完成"
}

# 主函数
main() {
    echo "=================================================="
    echo "  NVIDIA Tesla V100 SXM2 32GB 驱动自动安装脚本"
    echo "=================================================="
    echo ""
    
    check_root
    check_system
    check_gpu
    install_dependencies
    disable_nouveau
    
    # 检测是否为Ubuntu系统
    if [ -f /etc/lsb-release ] && grep -q "Ubuntu" /etc/lsb-release; then
        print_info "检测到Ubuntu系统，使用ubuntu-drivers工具安装驱动"
        install_driver_ubuntu
    else
        print_info "非Ubuntu系统，使用手动安装方式"
        install_driver_manual
    fi
    
    verify_installation
    
    # 清理未使用的驱动
    clean_unused_drivers
    
    install_cuda
    cleanup
    
    print_success "NVIDIA Tesla V100 驱动安装完成!"
    print_info "如果您在安装过程中选择了不重启系统，建议现在重启以确保所有更改生效"
    print_info "重启命令: sudo reboot"
}

# 执行主函数
main