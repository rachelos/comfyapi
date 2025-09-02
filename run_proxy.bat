@echo off
echo 启动HTTP代理服务器...
echo 默认端口: 6777
echo 使用方法: 在浏览器中访问 http://localhost:6777/https://example.com

REM 检查dist目录中是否存在proxy.exe
if exist "dist\proxy.exe" (
    dist\proxy.exe --host localhost --port 6777
) else (
    REM 如果没有找到打包的exe，则尝试运行Python脚本
    echo 未找到打包的可执行文件，尝试运行Python脚本...
    python proxy.py --host localhost --port 6777
)

pause