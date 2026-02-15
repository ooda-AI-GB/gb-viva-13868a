from fastapi import APIRouter, Depends, Request, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import app.routes as routes_module
from app.routes import get_current_user
from typing import Any
import os

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request):
    # Pass user if logged in, but don't require it
    # We can try to get user from request state or session if available, 
    # but viv-auth middleware usually handles this. 
    # For simplicity and given the spec "PUBLIC, no auth", we might just pass None 
    # or let the template handle it if we can extract user.
    # The layout usually needs 'user' to show Login/Logout.
    # viv-auth usually injects user into request.state.user if authenticated?
    # Or we can make it optional depend.
    # Let's check how main.py sets up auth. 
    # require_auth is the dependency.
    # We can try to get user optionally.
    # For now, let's pass user=None explicitly if not easily available, 
    # or rely on a "try_get_current_user" dependency if we had one.
    # But wait, existing code had `user=None` in the template response.
    # Let's stick to that for public page, but if user is logged in, it's nice to show it.
    # I'll just leave it as None for now to be safe and simple, or 
    # check if I can define an optional dependency.
    # The spec says "GET /pricing -> billing/pricing.html (PUBLIC, no auth)".
    return templates.TemplateResponse("billing/pricing.html", {"request": request, "user": None})

@router.post("/subscribe")
async def subscribe(request: Request, user: Any = Depends(get_current_user)):
    if not routes_module.create_checkout:
        raise HTTPException(status_code=500, detail="Billing not configured")

    price_id = os.environ.get("STRIPE_PRICE_ID", "")
    if not price_id:
        raise HTTPException(status_code=500, detail="STRIPE_PRICE_ID not set")

    try:
        url = routes_module.create_checkout(user_id=user.id, email=user.email, price_id=price_id)
        return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checkout failed: {str(e)[:200]}")
