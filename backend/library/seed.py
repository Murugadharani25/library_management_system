from .db import users, books, members, settings as settings_collection
from werkzeug.security import generate_password_hash
from datetime import datetime


def seed():
    # --- Admin user ---
    if users.count_documents({}) == 0:
        users.insert_many([
            {
                "name": "Library Admin",
                "email": "admin@library.com",
                "password": generate_password_hash("admin123"),
                "role": "admin",
            },
            {
                "name": "Demo Student",
                "email": "student@library.com",
                "password": generate_password_hash("student123"),
                "role": "student",
            },
            {
                "name": "Demo Teacher",
                "email": "teacher@library.com",
                "password": generate_password_hash("teacher123"),
                "role": "teacher",
            },
        ])

    # --- Demo books ---
    if books.count_documents({}) == 0:
        books.insert_many([
            {
                "title": "Clean Code",
                "author": "Robert C. Martin",
                "isbn": "9780132350884",
                "category": "Programming",
                "publisher": "Prentice Hall",
                "year": 2008,
                "total_copies": 4,
                "available_copies": 4,
                "shelf": "P-01",
            },
            {
                "title": "Python Crash Course",
                "author": "Eric Matthes",
                "isbn": "9781593279288",
                "category": "Programming",
                "publisher": "No Starch Press",
                "year": 2023,
                "total_copies": 5,
                "available_copies": 5,
                "shelf": "P-02",
            },
            {
                "title": "Atomic Habits",
                "author": "James Clear",
                "isbn": "9780735211292",
                "category": "Self Help",
                "publisher": "Avery",
                "year": 2018,
                "total_copies": 3,
                "available_copies": 3,
                "shelf": "S-01",
            },
        ])

    # --- Demo members (linked to users) ---
    if members.count_documents({}) == 0:
        student_user = users.find_one({"email": "student@library.com"})
        teacher_user = users.find_one({"email": "teacher@library.com"})

        member_docs = []

        if student_user:
            member_docs.append({
                "name": "Demo Student",
                "email": "student@library.com",
                "phone": "9876543210",
                "role": "student",
                "department": "Computer Science",
                "year": "3",
                "join_date": datetime.now(),
                "status": "Active",
                "user_id": str(student_user["_id"]),
            })

        if teacher_user:
            member_docs.append({
                "name": "Demo Teacher",
                "email": "teacher@library.com",
                "phone": "9876543211",
                "role": "teacher",
                "department": "Computer Science",
                "year": "",
                "join_date": datetime.now(),
                "status": "Active",
                "user_id": str(teacher_user["_id"]),
            })

        if member_docs:
            members.insert_many(member_docs)

    # --- Default settings ---
    if settings_collection.count_documents({}) == 0:
        settings_collection.insert_one({
            "loan_period_days": 14,
            "fine_per_day": 5,
            "maximum_fine": 500,
            "updated_by": "system",
            "updated_at": datetime.now(),
        })
