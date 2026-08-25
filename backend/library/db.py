import os
from pymongo import MongoClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGO_DB", "library_management")]
users = db.users
books = db.books
members = db.members
transactions = db.transactions
reservations = db.reservations
settings = db.settings
book_requests = db.book_requests
