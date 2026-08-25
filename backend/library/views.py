import json
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from werkzeug.security import check_password_hash

from .db import (
    users as users_collection,
    books as books_collection,
    members as members_collection,
    transactions as transactions_collection,
    reservations as reservations_collection,
)

from .serializers import clean
from .auth import token_for, require_auth
from .seed import seed


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def parse(request):
    try:
        return json.loads(request.body or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}


def valid_object_id(value):
    return bool(value and ObjectId.is_valid(value))


# ---------------------------------------------------------
# Authentication
# ---------------------------------------------------------

@csrf_exempt
def login(request):
    if request.method != "POST":
        return JsonResponse(
            {"detail": "POST required"},
            status=405
        )

    data = parse(request)

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return JsonResponse(
            {"detail": "Email and password are required"},
            status=400
        )

    user = users_collection.find_one({"email": email})

    if not user:
        return JsonResponse(
            {"detail": "Invalid email or password"},
            status=401
        )

    stored_password = user.get("password", "")

    try:
        password_valid = check_password_hash(
            stored_password,
            password
        )
    except Exception:
        password_valid = False

    if not password_valid:
        return JsonResponse(
            {"detail": "Invalid email or password"},
            status=401
        )

    return JsonResponse({
        "token": token_for(user),
        "user": {
            "id": str(user["_id"]),
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "role": user.get("role", "student"),
        }
    })


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

@require_auth
def dashboard(request):

    if request.method != "GET":
        return JsonResponse(
            {"detail": "GET required"},
            status=405
        )

    today = datetime.now(timezone.utc).replace(tzinfo=None)

    total_books = books_collection.count_documents({})

    available_books = sum(
        book.get("available_copies", 0)
        for book in books_collection.find(
            {},
            {"available_copies": 1}
        )
    )

    issued_books = transactions_collection.count_documents({
        "status": "Issued"
    })

    member_count = members_collection.count_documents({})

    overdue_count = transactions_collection.count_documents({
        "status": "Issued",
        "due_date": {"$lt": today}
    })

    pending_fines = sum(
        transaction.get("fine", 0)
        for transaction in transactions_collection.find(
            {"fine": {"$gt": 0}},
            {"fine": 1}
        )
    )

    return JsonResponse({
        "total_books": total_books,
        "available_books": available_books,
        "issued_books": issued_books,
        "members": member_count,
        "overdue": overdue_count,
        "pending_fines": pending_fines,
    })


# ---------------------------------------------------------
# Book Management
# ---------------------------------------------------------

@csrf_exempt
@require_auth
def books(request, book_id=None):

    # -------------------------
    # GET - List books
    # -------------------------

    if request.method == "GET":

        query = request.GET.get("q", "").strip()

        filters = {}

        if query:
            filters = {
                "$or": [
                    {
                        "title": {
                            "$regex": query,
                            "$options": "i"
                        }
                    },
                    {
                        "author": {
                            "$regex": query,
                            "$options": "i"
                        }
                    },
                    {
                        "isbn": {
                            "$regex": query,
                            "$options": "i"
                        }
                    },
                    {
                        "category": {
                            "$regex": query,
                            "$options": "i"
                        }
                    },
                ]
            }

        book_list = [
            clean(book)
            for book in books_collection.find(filters).sort(
                "title",
                1
            )
        ]

        return JsonResponse({
            "books": book_list
        })


    # Only admin can modify books

    if request.user_claims.get("role") != "admin":
        return JsonResponse(
            {"detail": "Admin only"},
            status=403
        )


    # -------------------------
    # POST - Add book
    # -------------------------

    if request.method == "POST":

        data = parse(request)

        required_fields = [
            "title",
            "author",
            "isbn",
            "category"
        ]

        missing = [
            field
            for field in required_fields
            if not data.get(field)
        ]

        if missing:
            return JsonResponse({
                "detail": "Missing required fields",
                "fields": missing
            }, status=400)

        try:
            total_copies = int(
                data.get("total_copies", 1)
            )
        except (ValueError, TypeError):
            total_copies = 1

        if total_copies < 1:
            total_copies = 1

        try:
            year = int(
                data.get(
                    "year",
                    datetime.now().year
                )
            )
        except (ValueError, TypeError):
            year = datetime.now().year

        # Check duplicate ISBN

        existing = books_collection.find_one({
            "isbn": data["isbn"]
        })

        if existing:
            return JsonResponse({
                "detail": "A book with this ISBN already exists"
            }, status=409)

        book_data = {
            "title": data["title"].strip(),
            "author": data["author"].strip(),
            "isbn": data["isbn"].strip(),
            "category": data["category"].strip(),
            "publisher": data.get("publisher", "").strip(),
            "year": year,
            "total_copies": total_copies,
            "available_copies": total_copies,
            "shelf": data.get("shelf", "").strip(),
            "created_at": datetime.now(),
        }

        result = books_collection.insert_one(book_data)

        created_book = books_collection.find_one({
            "_id": result.inserted_id
        })

        return JsonResponse(
            clean(created_book),
            status=201
        )


    # -------------------------
    # PUT/PATCH - Update book
    # -------------------------

    if request.method in ("PUT", "PATCH"):

        if not book_id or not valid_object_id(book_id):
            return JsonResponse({
                "detail": "Invalid book ID"
            }, status=400)

        data = parse(request)

        data.pop("id", None)
        data.pop("_id", None)

        # Don't allow invalid copy values

        if "total_copies" in data:

            try:
                data["total_copies"] = int(
                    data["total_copies"]
                )
            except (ValueError, TypeError):
                return JsonResponse({
                    "detail": "Invalid total_copies"
                }, status=400)

        data["updated_at"] = datetime.now()

        result = books_collection.update_one(
            {"_id": ObjectId(book_id)},
            {"$set": data}
        )

        if result.matched_count == 0:
            return JsonResponse({
                "detail": "Book not found"
            }, status=404)

        updated_book = books_collection.find_one({
            "_id": ObjectId(book_id)
        })

        return JsonResponse(
            clean(updated_book)
        )


    # -------------------------
    # DELETE - Delete book
    # -------------------------

    if request.method == "DELETE":

        if not book_id or not valid_object_id(book_id):
            return JsonResponse({
                "detail": "Invalid book ID"
            }, status=400)

        result = books_collection.delete_one({
            "_id": ObjectId(book_id)
        })

        if result.deleted_count == 0:
            return JsonResponse({
                "detail": "Book not found"
            }, status=404)

        return JsonResponse({
            "message": "Book deleted successfully"
        })


    return JsonResponse({
        "detail": "Method not allowed"
    }, status=405)


# ---------------------------------------------------------
# Members
# ---------------------------------------------------------

@csrf_exempt
@require_auth
def members(request):

    # GET members

    if request.method == "GET":

        member_list = [
            clean(member)
            for member in members_collection.find().sort(
                "name",
                1
            )
        ]

        return JsonResponse({
            "members": member_list
        })


    # Only admin can create members

    if request.user_claims.get("role") != "admin":
        return JsonResponse(
            {"detail": "Admin only"},
            status=403
        )


    # POST member

    if request.method == "POST":

        data = parse(request)

        if not data.get("name") or not data.get("email"):
            return JsonResponse({
                "detail": "Name and email are required"
            }, status=400)

        existing = members_collection.find_one({
            "email": data["email"].strip().lower()
        })

        if existing:
            return JsonResponse({
                "detail": "Member already exists"
            }, status=409)

        member_data = {
            "name": data["name"].strip(),
            "email": data["email"].strip().lower(),
            "phone": data.get("phone", "").strip(),
            "department": data.get(
                "department",
                ""
            ).strip(),
            "year": str(
                data.get("year", "")
            ),
            "join_date": datetime.now(),
            "status": data.get(
                "status",
                "Active"
            ),
        }

        result = members_collection.insert_one(
            member_data
        )

        created_member = members_collection.find_one({
            "_id": result.inserted_id
        })

        return JsonResponse(
            clean(created_member),
            status=201
        )


    return JsonResponse({
        "detail": "Method not allowed"
    }, status=405)


# ---------------------------------------------------------
# Transactions - List
# ---------------------------------------------------------

@csrf_exempt
@require_auth
def transactions(request):

    if request.method != "GET":
        return JsonResponse({
            "detail": "GET required"
        }, status=405)

    transaction_list = []

    for transaction in transactions_collection.find().sort(
        "issue_date",
        -1
    ):

        item = clean(transaction)

        book_id = item.get("book_id")

        book = None

        if valid_object_id(book_id):
            book = books_collection.find_one({
                "_id": ObjectId(book_id)
            })

        item["book_title"] = (
            book.get("title")
            if book
            else "Unknown Book"
        )

        member_id = item.get("member_id")

        member = None

        if valid_object_id(member_id):
            member = members_collection.find_one({
                "_id": ObjectId(member_id)
            })

        item["member_name"] = (
            member.get("name")
            if member
            else "Unknown Member"
        )

        transaction_list.append(item)

    return JsonResponse({
        "transactions": transaction_list
    })


# ---------------------------------------------------------
# Issue Book
# ---------------------------------------------------------

@csrf_exempt
@require_auth
def issue_book(request):

    if request.method != "POST":
        return JsonResponse({
            "detail": "POST required"
        }, status=405)

    data = parse(request)

    book_id = data.get("book_id")
    member_id = data.get("member_id")

    if not valid_object_id(book_id):
        return JsonResponse({
            "detail": "Invalid book ID"
        }, status=400)

    if not valid_object_id(member_id):
        return JsonResponse({
            "detail": "Invalid member ID"
        }, status=400)

    book = books_collection.find_one({
        "_id": ObjectId(book_id)
    })

    if not book:
        return JsonResponse({
            "detail": "Book not found"
        }, status=404)

    member = members_collection.find_one({
        "_id": ObjectId(member_id)
    })

    if not member:
        return JsonResponse({
            "detail": "Member not found"
        }, status=404)

    if book.get("available_copies", 0) < 1:
        return JsonResponse({
            "detail": "Book is currently unavailable"
        }, status=400)

    # Prevent same member from issuing same book twice

    existing_issue = transactions_collection.find_one({
        "book_id": book_id,
        "member_id": member_id,
        "status": "Issued"
    })

    if existing_issue:
        return JsonResponse({
            "detail": "This member already has this book"
        }, status=400)

    issue_date = datetime.now()

    try:
        loan_days = int(
            data.get("days", 14)
        )
    except (ValueError, TypeError):
        loan_days = 14

    if loan_days < 1:
        loan_days = 14

    due_date = issue_date + timedelta(
        days=loan_days
    )

    transaction_data = {
        "book_id": book_id,
        "member_id": member_id,
        "issue_date": issue_date,
        "due_date": due_date,
        "return_date": None,
        "fine": 0,
        "status": "Issued",
    }

    transactions_collection.insert_one(
        transaction_data
    )

    books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {
            "$inc": {
                "available_copies": -1
            }
        }
    )

    return JsonResponse({
        "message": "Book issued successfully",
        "due_date": due_date.isoformat()
    }, status=201)


# ---------------------------------------------------------
# Return Book
# ---------------------------------------------------------

@csrf_exempt
@require_auth
def return_book(request, tx_id):

    if request.method != "POST":
        return JsonResponse({
            "detail": "POST required"
        }, status=405)

    if not valid_object_id(tx_id):
        return JsonResponse({
            "detail": "Invalid transaction ID"
        }, status=400)

    transaction = transactions_collection.find_one({
        "_id": ObjectId(tx_id)
    })

    if not transaction:
        return JsonResponse({
            "detail": "Transaction not found"
        }, status=404)

    if transaction.get("status") != "Issued":
        return JsonResponse({
            "detail": "This book has already been returned"
        }, status=400)

    return_date = datetime.now()

    due_date = transaction.get(
        "due_date",
        return_date
    )

    late_days = max(
        0,
        (return_date - due_date).days
    )

    # Fine = ₹5 per late day

    fine_per_day = 5
    fine = late_days * fine_per_day

    transactions_collection.update_one(
        {"_id": ObjectId(tx_id)},
        {
            "$set": {
                "return_date": return_date,
                "status": "Returned",
                "fine": fine,
            }
        }
    )

    book_id = transaction.get("book_id")

    if valid_object_id(book_id):

        books_collection.update_one(
            {"_id": ObjectId(book_id)},
            {
                "$inc": {
                    "available_copies": 1
                }
            }
        )

    return JsonResponse({
        "message": "Book returned successfully",
        "late_days": late_days,
        "fine": fine
    })


# ---------------------------------------------------------
# Reservations
# ---------------------------------------------------------

@csrf_exempt
@require_auth
def reservations(request):

    # GET reservations

    if request.method == "GET":

        reservation_list = [
            clean(reservation)
            for reservation in reservations_collection.find().sort(
                "created_at",
                -1
            )
        ]

        return JsonResponse({
            "reservations": reservation_list
        })


    # POST reservation

    if request.method == "POST":

        data = parse(request)

        book_id = data.get("book_id")
        member_id = data.get("member_id")

        if not valid_object_id(book_id):
            return JsonResponse({
                "detail": "Invalid book ID"
            }, status=400)

        if not valid_object_id(member_id):
            return JsonResponse({
                "detail": "Invalid member ID"
            }, status=400)

        book = books_collection.find_one({
            "_id": ObjectId(book_id)
        })

        if not book:
            return JsonResponse({
                "detail": "Book not found"
            }, status=404)

        member = members_collection.find_one({
            "_id": ObjectId(member_id)
        })

        if not member:
            return JsonResponse({
                "detail": "Member not found"
            }, status=404)

        # Prevent duplicate active reservation

        existing = reservations_collection.find_one({
            "book_id": book_id,
            "member_id": member_id,
            "status": "Waiting"
        })

        if existing:
            return JsonResponse({
                "detail": "Reservation already exists"
            }, status=409)

        reservation_data = {
            "book_id": book_id,
            "member_id": member_id,
            "created_at": datetime.now(),
            "status": "Waiting",
        }

        reservations_collection.insert_one(
            reservation_data
        )

        return JsonResponse({
            "message": "Book reserved successfully"
        }, status=201)


    return JsonResponse({
        "detail": "Method not allowed"
    }, status=405)


# ---------------------------------------------------------
# Seed Demo Data
# ---------------------------------------------------------

@csrf_exempt
def seed_data(request):

    if request.method not in ("GET", "POST"):
        return JsonResponse({
            "detail": "GET or POST required"
        }, status=405)

    try:
        seed()

        return JsonResponse({
            "message": "Demo data is ready",
            "admin_email": "admin@library.com",
            "admin_password": "admin123",
            "student_email": "student@library.com",
            "student_password": "student123",
        })

    except Exception as error:

        return JsonResponse({
            "detail": "Failed to create demo data",
            "error": str(error)
        }, status=500)