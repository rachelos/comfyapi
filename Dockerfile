
FROM  ghcr.io/rachelos/base-mini:latest
# 安装系统依赖
WORKDIR /app

# ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# 复制Python依赖文件
# 复制后端代码
COPY requirements.txt .
RUN pip3 install -r requirements.txt 
ADD . .
RUN chmod +x ./start.sh
# 暴露端口
EXPOSE 8081
# 启动命令
CMD ["./start.sh"]
# CMD ["sleep", "infinity"]