from django.urls import path
from . import views


urlpatterns = [
    # Authentication
    path(
        "auth/login/",
        views.login,
        name="login"
    ),

    # Dashboard
    path(
        "dashboard/",
        views.dashboard,
        name="dashboard"
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

    # Members
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