from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import Activity, Contact, Deal
import app.routes as routes_module
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/activities", response_class=HTMLResponse)
async def list_activities(
    request: Request,
    user=Depends(routes_module.get_current_user),
    subscription=Depends(routes_module.get_active_subscription),
    db: Session = Depends(get_db)
):
    activities = db.query(Activity).order_by(desc(Activity.created_at)).all()
    contacts = db.query(Contact).all()
    deals = db.query(Deal).all()
    return templates.TemplateResponse("activities/list.html", {
        "request": request,
        "activities": activities,
        "contacts": contacts,
        "deals": deals,
        "user": user
    })

@router.post("/activities")
async def create_activity(
    request: Request,
    contact_id: int = Form(...),
    deal_id: int = Form(None),
    type: str = Form(...),
    subject: str = Form(...),
    description: str = Form(None),
    date_str: str = Form(...), # expecting YYYY-MM-DDTHH:MM
    user=Depends(routes_module.get_current_user),
    subscription=Depends(routes_module.get_active_subscription),
    db: Session = Depends(get_db)
):
    try:
        activity_date = datetime.fromisoformat(date_str)
    except ValueError:
        # handle different format if needed, but HTML datetime-local uses ISO
        activity_date = datetime.now()

    activity = Activity(
        contact_id=contact_id,
        deal_id=deal_id,
        type=type,
        subject=subject,
        description=description,
        date=activity_date
    )
    db.add(activity)
    db.commit()
    return RedirectResponse(url="/activities", status_code=303)

@router.post("/activities/{id}/complete")
async def complete_activity(
    request: Request,
    id: int,
    user=Depends(routes_module.get_current_user),
    subscription=Depends(routes_module.get_active_subscription),
    db: Session = Depends(get_db)
):
    activity = db.query(Activity).filter(Activity.id == id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    activity.completed = True
    db.commit()
    return RedirectResponse(url="/activities", status_code=303)
