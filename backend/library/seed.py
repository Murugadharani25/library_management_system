from .db import users, books, members
from werkzeug.security import generate_password_hash
from datetime import datetime

def seed():
    if users.count_documents({}) == 0:
        users.insert_many([
            {"name":"Library Admin","email":"admin@library.com","password":generate_password_hash("admin123"),"role":"admin"},
            {"name":"Demo Student","email":"student@library.com","password":generate_password_hash("student123"),"role":"student"},
        ])
    if books.count_documents({}) == 0:
        books.insert_many([
            {"title":"Clean Code","author":"Robert C. Martin","isbn":"9780132350884","category":"Programming","publisher":"Prentice Hall","year":2008,"total_copies":4,"available_copies":4,"shelf":"P-01"},
            {"title":"Python Crash Course","author":"Eric Matthes","isbn":"9781593279288","category":"Programming","publisher":"No Starch Press","year":2023,"total_copies":5,"available_copies":5,"shelf":"P-02"},
            {"title":"Atomic Habits","author":"James Clear","isbn":"9780735211292","category":"Self Help","publisher":"Avery","year":2018,"total_copies":3,"available_copies":3,"shelf":"S-01"},
        ])
    if members.count_documents({}) == 0:
        users_doc = users.find_one({"email":"student@library.com"})
        members.insert_one({"name":"Demo Student","email":"student@library.com","phone":"9876543210","department":"Computer Science","year":"3","join_date":datetime.now(),"status":"Active","user_id":str(users_doc["_id"])})
