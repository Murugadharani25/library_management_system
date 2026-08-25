FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["sh","-c","python -c 'from library.seed import seed; seed()' && python manage.py runserver 0.0.0.0:8000"]
