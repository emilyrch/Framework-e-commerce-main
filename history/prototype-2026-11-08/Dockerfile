FROM python:3.11-slim
WORKDIR /app
COPY lps ./lps
COPY services ./services
COPY configurations ./configurations
ENTRYPOINT ["python", "-m", "services.server"]
