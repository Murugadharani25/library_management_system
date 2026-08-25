import os, jwt
from datetime import datetime, timedelta, timezone
from django.http import JsonResponse
from functools import wraps

SECRET = os.getenv("JWT_SECRET", "dev-secret")

def token_for(user):
    payload = {"sub": str(user["_id"]), "role": user["role"], "email": user["email"],
               "exp": datetime.now(timezone.utc) + timedelta(hours=12)}
    return jwt.encode(payload, SECRET, algorithm="HS256")

def current_user(request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "): return None
    try:
        return jwt.decode(header.split(" ",1)[1], SECRET, algorithms=["HS256"])
    except Exception:
        return None

def require_auth(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = current_user(request)
        if not user: return JsonResponse({"detail":"Authentication required"}, status=401)
        request.user_claims = user
        return view(request, *args, **kwargs)
    return wrapper
