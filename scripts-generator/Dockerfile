FROM python:3.11-slim
WORKDIR /app

# 1) Install dependencies
COPY scripts-generator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy only the code for this service
COPY scripts-generator/script_generator.py .
COPY scripts-generator/config.py        .

# 3) Copy shared code
COPY common ./common

CMD ["python", "script_generator.py"]
