FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 mdl \
    && mkdir /data && chown mdl:mdl /data
WORKDIR /app
COPY requirements.lock ./
RUN python -m pip install -r requirements.lock
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-deps .
USER mdl
ENV MDL_TOKEN_FILE=/data/token.json MDL_MCP_HOST=0.0.0.0
EXPOSE 8000
ENTRYPOINT ["mydramalist-mcp"]
CMD ["serve", "--transport", "http"]

