echo off
chcp 65001
set name=comfyapi
REM 构建镜像
docker build -t %name% .
REM 获取所有运行中容器的ID并逐个停止
FOR /f "tokens=*" %%i IN ('docker ps -q') DO docker stop %%i
docker container prune -f

docker run -d --name %name% -p 8002:8001 -v %~dp0:/work %name%
docker exec -it %name% /bin/bash

if "%1"=="-p" (
docker image tag %name% ghcr.io/rachelos/%name%:latest
docker image ls
docker push ghcr.io/rachelos/%name%:latest
)
docker stop %name%