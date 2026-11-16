# 第一阶段：只准备精简后的 Python 依赖，可单独打标签长期复用
FROM python:3.14-alpine AS deps
WORKDIR /app
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
RUN python -m venv "$VIRTUAL_ENV"
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple -r requirements.txt \
    || pip install --no-cache-dir -r requirements.txt

# 清理必须和安装放在同一层，否则旧层仍占镜像体积。
# TRIM_I18N=1 可再删除 SQLAdmin 后台的 babel 语言包（约 31MB），后台页面仍可用，但国际化显示会退化。
ARG TRIM_I18N=0
RUN rm -rf /opt/venv/lib/python3.14/site-packages/pip \
           /opt/venv/lib/python3.14/site-packages/pip-*.dist-info \
           /opt/venv/bin/pip /opt/venv/bin/pip3 /opt/venv/bin/pip3.14 \
           /opt/venv/lib/python3.14/site-packages/sqlalchemy/testing \
    && if [ "$TRIM_I18N" = "1" ]; then \
         rm -rf /opt/venv/lib/python3.14/site-packages/babel/locale-data; \
       fi \
    && find /opt/venv -type d -name __pycache__ -prune -exec rm -rf {} + \
    && find /opt/venv -name '*.pyc' -delete

# 第二阶段：运行镜像，只带入精简依赖和项目代码
FROM python:3.14-alpine AS runtime
WORKDIR /app
COPY --from=deps /opt/venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
COPY . .
RUN mkdir -p /data
ENV DB_PATH=/data/tokens.db
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
