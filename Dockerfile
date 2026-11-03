FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY PROMPT.MD .

RUN mkdir -p output models

CMD ["python", "-m", "src.run_weekly"]
