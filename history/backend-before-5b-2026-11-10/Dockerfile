FROM python:3.11.0-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY foundation ./foundation
COPY domain ./domain
COPY services/catalog ./services/catalog
COPY services/orders ./services/orders
COPY services/payments ./services/payments
COPY services/__init__.py ./services/__init__.py
COPY shared ./shared
RUN mkdir /data && useradd --uid 10001 --no-create-home app && chown app /data
USER app
CMD ["python", "-m", "uvicorn", "services.catalog.app:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
