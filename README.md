# Smart Library Management System

Full-stack mini project built with React, Django REST Framework, and MongoDB.

## Features
- Admin and student authentication
- Dashboard statistics
- Book CRUD
- Member management
- Issue and return books
- Automatic fine calculation
- Book reservations
- Search/filter books
- Transaction history
- Responsive React UI

## Requirements
- Python 3.10+
- Node.js 18+
- MongoDB running locally or a MongoDB Atlas URI

## Backend setup

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
python manage.py runserver
```

## Frontend setup
```bash
cd frontend
npm install
npm run dev
```

Default frontend: http://localhost:5173
Default backend: http://127.0.0.1:8000

Demo login:
- Admin: admin@library.com / admin123
- Student: student@library.com / student123

On first backend start, demo users and books are created automatically.
