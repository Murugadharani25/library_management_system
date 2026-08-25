import json
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from werkzeug.security import check_password_hash, generate_password_hash

from .db import (
    users as users_collection,
    books as books_collection,
    members as members_collection,
    transactions as transactions_collection,
    reservations as reservations_collection,
    settings as settings_collection,
    book_requests as book_requests_collection,
)

from .serializers import clean
from .auth import token_for, require_auth, require_admin
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


def get_settings():
    """Retrieve library settings from MongoDB (with fallback defaults)."""
    doc = settings_collection.find_one({})
    if not doc:
        return {
            "loan_period_days": 14,
            "fine_per_day": 5,
            "maximum_fine": 500,
        }
    return {
        "loan_period_days": doc.get("loan_period_days", 14),
        "fine_per_day": doc.get("fine_per_day", 5),
        "maximum_fine": doc.get("maximum_fine", 500),
    }


def get_member_for_user(user_id):
    """Find the member document linked to a user ID."""
    return members_collection.find_one({"user_id": user_id})


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

    # Build response user info
    user_info = {
        "id": str(user["_id"]),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "student"),
    }

    # For student/teacher, include their member_id
    if user_info["role"] in ("student", "teacher"):
        member = get_member_for_user(str(user["_id"]))
        if member:
            user_info["member_id"] = str(member["_id"])

    return JsonResponse({
        "token": token_for(user),
        "user": user_info,
    })


# ---------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------

@require_admin
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

    pending_requests = book_requests_collection.count_documents({
        "status": "Pending"
    })

    return JsonResponse({
        "total_books": total_books,
        "available_books": available_books,
        "issued_books": issued_books,
        "members": member_count,
        "overdue": overdue_count,
        "pending_fines": pending_fines,
        "pending_requests": pending_requests,
    })


# ---------------------------------------------------------
# My Dashboard (Student / Teacher)
# ---------------------------------------------------------

@require_auth
def my_dashboard(request):

    if request.method != "GET":
        return JsonResponse(
            {"detail": "GET required"},
            status=405
        )

    user_id = request.user_claims.get("sub")
    role = request.user_claims.get("role", "")

    # Admins should use the /dashboard/ endpoint
    if role == "admin":
        return JsonResponse(
            {"detail": "Use /api/dashboard/ for admin"},
            status=400
        )

    member = get_member_for_user(user_id)

    # Library-wide stats (visible to all users)
    total_books = books_collection.count_documents({})
    total_available = sum(
        b.get("available_copies", 0)
        for b in books_collection.find({}, {"available_copies": 1})
    )

    if not member:
        return JsonResponse({
            "name": request.user_claims.get("name", ""),
            "role": role,
            "total_books": total_books,
            "total_available": total_available,
            "issued_books": [],
            "history": [],
            "my_requests": [],
            "total_fine_pending": 0,
            "total_fine_paid": 0,
        })

    member_id = str(member["_id"])

    # Currently issued books
    issued_txs = list(transactions_collection.find({
        "member_id": member_id,
        "status": "Issued",
    }))

    issued_books = []
    total_fine_pending = 0

    today = datetime.now(timezone.utc).replace(tzinfo=None)
    lib_settings = get_settings()

    for tx in issued_txs:
        book = None
        book_id = tx.get("book_id")
        if valid_object_id(book_id):
            book = books_collection.find_one({"_id": ObjectId(book_id)})

        due_date = tx.get("due_date", today)
        late_days = max(0, (today - due_date).days)
        current_fine = min(
            late_days * lib_settings["fine_per_day"],
            lib_settings["maximum_fine"]
        )
        total_fine_pending += current_fine

        issued_books.append({
            "id": str(tx["_id"]),
            "book_title": book.get("title") if book else "Unknown Book",
            "book_author": book.get("author") if book else "",
            "issue_date": tx.get("issue_date", "").isoformat() if isinstance(tx.get("issue_date"), datetime) else str(tx.get("issue_date", "")),
            "due_date": due_date.isoformat() if isinstance(due_date, datetime) else str(due_date),
            "late_days": late_days,
            "fine": current_fine,
        })

    # Borrowing history (returned books)
    history_txs = list(transactions_collection.find({
        "member_id": member_id,
        "status": "Returned",
    }).sort("return_date", -1))

    history = []
    total_fine_paid = 0

    for tx in history_txs:
        book = None
        book_id = tx.get("book_id")
        if valid_object_id(book_id):
            book = books_collection.find_one({"_id": ObjectId(book_id)})

        fine = tx.get("fine", 0)
        total_fine_paid += fine

        history.append({
            "id": str(tx["_id"]),
            "book_title": book.get("title") if book else "Unknown Book",
            "book_author": book.get("author") if book else "",
            "issue_date": tx.get("issue_date", "").isoformat() if isinstance(tx.get("issue_date"), datetime) else str(tx.get("issue_date", "")),
            "due_date": tx.get("due_date", "").isoformat() if isinstance(tx.get("due_date"), datetime) else str(tx.get("due_date", "")),
            "return_date": tx.get("return_date", "").isoformat() if isinstance(tx.get("return_date"), datetime) else str(tx.get("return_date", "")),
            "fine": fine,
        })

    # My book requests
    my_reqs = list(book_requests_collection.find({
        "user_id": user_id,
    }).sort("requested_at", -1))

    my_requests = []
    for req in my_reqs:
        book = None
        bid = req.get("book_id")
        if valid_object_id(bid):
            book = books_collection.find_one({"_id": ObjectId(bid)})
        my_requests.append({
            "id": str(req["_id"]),
            "book_id": bid,
            "book_title": book.get("title") if book else "Unknown Book",
            "book_author": book.get("author") if book else "",
            "requested_at": req.get("requested_at", "").isoformat() if isinstance(req.get("requested_at"), datetime) else str(req.get("requested_at", "")),
            "status": req.get("status", "Pending"),
        })

    # Count pending returns (issued books = pending returns)
    pending_returns = len(issued_books)

    # Count my pending requests
    my_pending_requests = book_requests_collection.count_documents({
        "user_id": user_id,
        "status": "Pending",
    })

    return JsonResponse({
        "name": member.get("name", ""),
        "role": role,
        "department": member.get("department", ""),
        "email": member.get("email", ""),
        "total_books": total_books,
        "total_available": total_available,
        "my_issued_count": len(issued_books),
        "pending_returns": pending_returns,
        "my_pending_requests": my_pending_requests,
        "issued_books": issued_books,
        "history": history,
        "my_requests": my_requests,
        "total_fine_pending": total_fine_pending,
        "total_fine_paid": total_fine_paid,
    })


# ---------------------------------------------------------
# Book Management
# ---------------------------------------------------------

@csrf_exempt
@require_auth
def books(request, book_id=None):

    # -------------------------
    # GET - List books (all authenticated users can browse)
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
# Book Request (Student / Teacher)
# ---------------------------------------------------------

@csrf_exempt
@require_auth
def request_book(request, book_id):
    """Student/Teacher can request a book. POST only."""

    if request.method != "POST":
        return JsonResponse(
            {"detail": "POST required"},
            status=405
        )

    role = request.user_claims.get("role", "")
    user_id = request.user_claims.get("sub", "")

    # Only students and teachers can request books
    if role not in ("student", "teacher"):
        return JsonResponse(
            {"detail": "Only students and teachers can request books"},
            status=403
        )

    if not valid_object_id(book_id):
        return JsonResponse(
            {"detail": "Invalid book ID"},
            status=400
        )

    book = books_collection.find_one({"_id": ObjectId(book_id)})
    if not book:
        return JsonResponse(
            {"detail": "Book not found"},
            status=404
        )

    # Check for duplicate pending request
    existing = book_requests_collection.find_one({
        "book_id": book_id,
        "user_id": user_id,
        "status": "Pending",
    })

    if existing:
        return JsonResponse(
            {"detail": "You already have a pending request for this book"},
            status=409
        )

    # Also check if user already has this book issued
    member = get_member_for_user(user_id)
    if member:
        existing_issue = transactions_collection.find_one({
            "book_id": book_id,
            "member_id": str(member["_id"]),
            "status": "Issued",
        })
        if existing_issue:
            return JsonResponse(
                {"detail": "You already have this book issued"},
                status=400
            )

    request_data = {
        "book_id": book_id,
        "user_id": user_id,
        "role": role,
        "requested_at": datetime.now(),
        "status": "Pending",
        "issued_at": None,
        "issued_by": None,
    }

    book_requests_collection.insert_one(request_data)

    return JsonResponse({
        "message": "Book requested successfully",
        "status": "Pending",
    }, status=201)


# ---------------------------------------------------------
# My Requests (Student / Teacher)
# ---------------------------------------------------------

@require_auth
def my_requests(request):
    """GET own book requests."""

    if request.method != "GET":
        return JsonResponse(
            {"detail": "GET required"},
            status=405
        )

    user_id = request.user_claims.get("sub", "")

    reqs = list(book_requests_collection.find({
        "user_id": user_id,
    }).sort("requested_at", -1))

    request_list = []
    for req in reqs:
        book = None
        bid = req.get("book_id")
        if valid_object_id(bid):
            book = books_collection.find_one({"_id": ObjectId(bid)})

        request_list.append({
            "id": str(req["_id"]),
            "book_id": bid,
            "book_title": book.get("title") if book else "Unknown Book",
            "book_author": book.get("author") if book else "",
            "requested_at": req.get("requested_at", "").isoformat() if isinstance(req.get("requested_at"), datetime) else str(req.get("requested_at", "")),
            "status": req.get("status", "Pending"),
        })

    return JsonResponse({"requests": request_list})


# ---------------------------------------------------------
# My Books (Student / Teacher - currently issued)
# ---------------------------------------------------------

@require_auth
def my_books(request):
    """GET own currently issued books."""

    if request.method != "GET":
        return JsonResponse(
            {"detail": "GET required"},
            status=405
        )

    user_id = request.user_claims.get("sub", "")
    member = get_member_for_user(user_id)

    if not member:
        return JsonResponse({"books": []})

    member_id = str(member["_id"])
    today = datetime.now(timezone.utc).replace(tzinfo=None)
    lib_settings = get_settings()

    issued_txs = list(transactions_collection.find({
        "member_id": member_id,
        "status": "Issued",
    }))

    my_book_list = []
    for tx in issued_txs:
        book = None
        book_id = tx.get("book_id")
        if valid_object_id(book_id):
            book = books_collection.find_one({"_id": ObjectId(book_id)})

        due_date = tx.get("due_date", today)
        late_days = max(0, (today - due_date).days)
        fine = min(
            late_days * lib_settings["fine_per_day"],
            lib_settings["maximum_fine"]
        )

        my_book_list.append({
            "id": str(tx["_id"]),
            "book_title": book.get("title") if book else "Unknown Book",
            "book_author": book.get("author") if book else "",
            "issue_date": tx.get("issue_date", "").isoformat() if isinstance(tx.get("issue_date"), datetime) else str(tx.get("issue_date", "")),
            "due_date": due_date.isoformat() if isinstance(due_date, datetime) else str(due_date),
            "status": "Issued",
            "late_days": late_days,
            "fine": fine,
        })

    return JsonResponse({"books": my_book_list})


# ---------------------------------------------------------
# Admin: View All Book Requests
# ---------------------------------------------------------

@require_admin
def admin_book_requests(request):
    """GET all book requests (admin only)."""

    if request.method != "GET":
        return JsonResponse(
            {"detail": "GET required"},
            status=405
        )

    reqs = list(book_requests_collection.find().sort("requested_at", -1))

    request_list = []
    for req in reqs:
        # Get book info
        book = None
        bid = req.get("book_id")
        if valid_object_id(bid):
            book = books_collection.find_one({"_id": ObjectId(bid)})

        # Get user info
        user = None
        uid = req.get("user_id")
        if valid_object_id(uid):
            user = users_collection.find_one({"_id": ObjectId(uid)})

        # Get member info for member_id
        member = None
        if uid:
            member = get_member_for_user(uid)

        request_list.append({
            "id": str(req["_id"]),
            "book_id": bid,
            "book_title": book.get("title") if book else "Unknown Book",
            "book_author": book.get("author") if book else "",
            "book_available": book.get("available_copies", 0) if book else 0,
            "user_id": uid,
            "user_name": user.get("name") if user else "Unknown User",
            "user_email": user.get("email") if user else "",
            "role": req.get("role", ""),
            "member_id": str(member["_id"]) if member else None,
            "requested_at": req.get("requested_at", "").isoformat() if isinstance(req.get("requested_at"), datetime) else str(req.get("requested_at", "")),
            "status": req.get("status", "Pending"),
        })

    return JsonResponse({"requests": request_list})


# ---------------------------------------------------------
# Admin: Issue a Book Request
# ---------------------------------------------------------

@csrf_exempt
@require_admin
def admin_issue_request(request, request_id):
    """Admin issues a book from a pending request."""

    if request.method != "POST":
        return JsonResponse(
            {"detail": "POST required"},
            status=405
        )

    if not valid_object_id(request_id):
        return JsonResponse(
            {"detail": "Invalid request ID"},
            status=400
        )

    # Find the book request
    book_req = book_requests_collection.find_one({
        "_id": ObjectId(request_id)
    })

    if not book_req:
        return JsonResponse(
            {"detail": "Book request not found"},
            status=404
        )

    if book_req.get("status") != "Pending":
        return JsonResponse(
            {"detail": f"Request is already {book_req.get('status', 'processed')}"},
            status=400
        )

    book_id = book_req.get("book_id")
    user_id = book_req.get("user_id")

    # Validate book
    if not valid_object_id(book_id):
        return JsonResponse(
            {"detail": "Invalid book ID in request"},
            status=400
        )

    book = books_collection.find_one({"_id": ObjectId(book_id)})
    if not book:
        return JsonResponse(
            {"detail": "Book not found"},
            status=404
        )

    if book.get("available_copies", 0) < 1:
        return JsonResponse(
            {"detail": "No copies available. Cannot issue this book."},
            status=400
        )

    # Find the member for the requesting user
    member = get_member_for_user(user_id)
    if not member:
        return JsonResponse(
            {"detail": "No member record found for this user"},
            status=400
        )

    member_id = str(member["_id"])

    # Check if member already has this book
    existing_issue = transactions_collection.find_one({
        "book_id": book_id,
        "member_id": member_id,
        "status": "Issued",
    })

    if existing_issue:
        # Mark request as Issued since they already have it
        book_requests_collection.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {"status": "Issued", "issued_at": datetime.now(),
                       "issued_by": request.user_claims.get("email", "admin")}}
        )
        return JsonResponse(
            {"detail": "This member already has this book issued"},
            status=400
        )

    # Create the transaction
    lib_settings = get_settings()
    issue_date = datetime.now()
    due_date = issue_date + timedelta(days=lib_settings["loan_period_days"])

    transaction_data = {
        "book_id": book_id,
        "member_id": member_id,
        "issue_date": issue_date,
        "due_date": due_date,
        "return_date": None,
        "fine": 0,
        "status": "Issued",
    }

    transactions_collection.insert_one(transaction_data)

    # Decrease available copies
    books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {"$inc": {"available_copies": -1}}
    )

    # Update request status to Issued
    book_requests_collection.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {
            "status": "Issued",
            "issued_at": issue_date,
            "issued_by": request.user_claims.get("email", "admin"),
        }}
    )

    return JsonResponse({
        "message": "Book issued successfully from request",
        "due_date": due_date.isoformat(),
        "loan_days": lib_settings["loan_period_days"],
    }, status=201)


# ---------------------------------------------------------
# Members (Admin Only)
# ---------------------------------------------------------

@csrf_exempt
@require_admin
def members(request):

    # GET members (admin only)

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


    # POST member (admin only - creates member + login account)

    if request.method == "POST":

        data = parse(request)

        if not data.get("name") or not data.get("email"):
            return JsonResponse({
                "detail": "Name and email are required"
            }, status=400)

        email = data["email"].strip().lower()

        # Check if member already exists
        existing = members_collection.find_one({
            "email": email
        })

        if existing:
            return JsonResponse({
                "detail": "Member already exists"
            }, status=409)

        # Determine role (default to student)
        role = data.get("role", "student").strip().lower()
        if role not in ("student", "teacher"):
            role = "student"

        # Auto-create login account in users collection
        existing_user = users_collection.find_one({"email": email})

        if existing_user:
            user_id = str(existing_user["_id"])
        else:
            # Default password: <email-prefix>123
            email_prefix = email.split("@")[0]
            default_password = f"{email_prefix}123"

            user_data = {
                "name": data["name"].strip(),
                "email": email,
                "password": generate_password_hash(default_password),
                "role": role,
                "created_at": datetime.now(),
            }

            user_result = users_collection.insert_one(user_data)
            user_id = str(user_result.inserted_id)

        # Create the member document
        member_data = {
            "name": data["name"].strip(),
            "email": email,
            "phone": data.get("phone", "").strip(),
            "role": role,
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
            "user_id": user_id,
        }

        result = members_collection.insert_one(
            member_data
        )

        created_member = members_collection.find_one({
            "_id": result.inserted_id
        })

        # Return the created member with the default password info
        response = clean(created_member)
        if not existing_user:
            email_prefix = email.split("@")[0]
            response["default_password"] = f"{email_prefix}123"

        return JsonResponse(
            response,
            status=201
        )


    return JsonResponse({
        "detail": "Method not allowed"
    }, status=405)


# ---------------------------------------------------------
# Transactions
# ---------------------------------------------------------

@csrf_exempt
@require_auth
def transactions(request):

    if request.method != "GET":
        return JsonResponse({
            "detail": "GET required"
        }, status=405)

    role = request.user_claims.get("role", "")
    user_id = request.user_claims.get("sub", "")

    # Build query filter based on role
    query_filter = {}

    if role != "admin":
        # Student/Teacher: only see their own transactions
        member = get_member_for_user(user_id)
        if member:
            query_filter["member_id"] = str(member["_id"])
        else:
            # No member record found, return empty
            return JsonResponse({"transactions": []})

    transaction_list = []

    for transaction in transactions_collection.find(query_filter).sort(
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
# Issue Book (Admin Only)
# ---------------------------------------------------------

@csrf_exempt
@require_admin
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

    # Use loan period from settings
    lib_settings = get_settings()
    loan_days = lib_settings["loan_period_days"]

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
        "due_date": due_date.isoformat(),
        "loan_days": loan_days,
    }, status=201)


# ---------------------------------------------------------
# Return Book (Admin Only)
# ---------------------------------------------------------

@csrf_exempt
@require_admin
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

    # Fine from settings (not hardcoded)
    lib_settings = get_settings()
    fine_per_day = lib_settings["fine_per_day"]
    maximum_fine = lib_settings["maximum_fine"]

    fine = min(
        late_days * fine_per_day,
        maximum_fine
    )

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
# Library Settings (Admin Only)
# ---------------------------------------------------------

@csrf_exempt
@require_admin
def settings_view(request):

    # GET - Retrieve current settings
    if request.method == "GET":
        doc = settings_collection.find_one({})
        if not doc:
            return JsonResponse({
                "loan_period_days": 14,
                "fine_per_day": 5,
                "maximum_fine": 500,
            })
        return JsonResponse({
            "loan_period_days": doc.get("loan_period_days", 14),
            "fine_per_day": doc.get("fine_per_day", 5),
            "maximum_fine": doc.get("maximum_fine", 500),
        })

    # PUT - Update settings
    if request.method == "PUT":
        data = parse(request)

        update_fields = {}

        if "loan_period_days" in data:
            try:
                val = int(data["loan_period_days"])
                if val < 1:
                    val = 1
                update_fields["loan_period_days"] = val
            except (ValueError, TypeError):
                return JsonResponse({
                    "detail": "Invalid loan_period_days"
                }, status=400)

        if "fine_per_day" in data:
            try:
                val = int(data["fine_per_day"])
                if val < 0:
                    val = 0
                update_fields["fine_per_day"] = val
            except (ValueError, TypeError):
                return JsonResponse({
                    "detail": "Invalid fine_per_day"
                }, status=400)

        if "maximum_fine" in data:
            try:
                val = int(data["maximum_fine"])
                if val < 0:
                    val = 0
                update_fields["maximum_fine"] = val
            except (ValueError, TypeError):
                return JsonResponse({
                    "detail": "Invalid maximum_fine"
                }, status=400)

        if not update_fields:
            return JsonResponse({
                "detail": "No valid fields to update"
            }, status=400)

        update_fields["updated_by"] = request.user_claims.get("email", "admin")
        update_fields["updated_at"] = datetime.now()

        settings_collection.update_one(
            {},
            {"$set": update_fields},
            upsert=True
        )

        # Return updated settings
        doc = settings_collection.find_one({})
        return JsonResponse({
            "loan_period_days": doc.get("loan_period_days", 14),
            "fine_per_day": doc.get("fine_per_day", 5),
            "maximum_fine": doc.get("maximum_fine", 500),
            "message": "Settings updated successfully",
        })

    return JsonResponse({
        "detail": "Method not allowed"
    }, status=405)


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
            "teacher_email": "teacher@library.com",
            "teacher_password": "teacher123",
        })

    except Exception as error:

        return JsonResponse({
            "detail": "Failed to create demo data",
            "error": str(error)
        }, status=500)