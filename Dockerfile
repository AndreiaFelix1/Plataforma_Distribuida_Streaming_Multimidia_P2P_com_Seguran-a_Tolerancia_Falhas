FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

EXPOSE 9000 9101 9102 8081 8082

CMD ["python3", "src/server.py", "--host", "0.0.0.0", "--port", "9000"]
