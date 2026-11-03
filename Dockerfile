# Hosted ideavalidator remote MCP server (streamable HTTP). Deploy to Render/any container host.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-server.txt

COPY pipeline/ ./pipeline/
COPY server/ ./server/

ENV PORT=8000 IV_STORE=/data
EXPOSE 8000
CMD ["python", "-m", "server"]
