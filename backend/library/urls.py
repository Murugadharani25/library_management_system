from django.urls import path
from . import views


urlpatterns = [
    # Authentication
    path(
        "auth/login/",
        views.login,
        name="login"
    ),

    # Admin Dashboard
    path(
        "dashboard/",
        views.dashboard,
        name="dashboard"
    ),

    # Student / Teacher Personal Dashboard
    path(
        "my-dashboard/",
        views.my_dashboard,
        name="my-dashboard"
    ),

    # Books
    path(
        "books/",
        views.books,
        name="books"
    ),

    path(
        "books/<str:book_id>/",
        views.books,
        name="book-detail"
    ),

    # Book Request (Student / Teacher)
    path(
        "books/<str:book_id>/request/",
        views.request_book,
        name="request-book"
    ),

    # My Requests (Student / Teacher)
    path(
        "my-requests/",
        views.my_requests,
        name="my-requests"
    ),

    # My Books (Student / Teacher)
    path(
        "my-books/",
        views.my_books,
        name="my-books"
    ),

    # Admin: Book Requests Management
    path(
        "admin/book-requests/",
        views.admin_book_requests,
        name="admin-book-requests"
    ),

    path(
        "admin/book-requests/<str:request_id>/issue/",
        views.admin_issue_request,
        name="admin-issue-request"
    ),

    # Members (Admin Only)
    path(
        "members/",
        views.members,
        name="members"
    ),

    # Transactions
    path(
        "transactions/",
        views.transactions,
        name="transactions"
    ),

    path(
        "transactions/issue/",
        views.issue_book,
        name="issue-book"
    ),

    path(
        "transactions/<str:tx_id>/return/",
        views.return_book,
        name="return-book"
    ),

    # Library Settings (Admin Only)
    path(
        "settings/",
        views.settings_view,
        name="settings"
    ),

    # Reservations
    path(
        "reservations/",
        views.reservations,
        name="reservations"
    ),

    # Demo data
    path(
        "seed/",
        views.seed_data,
        name="seed-data"
    ),
]