from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database import get_db
from app.models import Contact, Deal, Activity
import app.routes as routes_module

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user=Depends(routes_module.get_current_user),
    subscription=Depends(routes_module.get_active_subscription),
    db: Session = Depends(get_db)
):
    # Quick stats
    total_contacts = db.query(Contact).count()
    open_deals_count = db.query(Deal).filter(Deal.stage.notin_(["closed_won", "closed_lost"])).count()
    total_pipeline_value = db.query(func.sum(Deal.value)).filter(Deal.stage.notin_(["closed_won", "closed_lost"])).scalar() or 0.0
    
    won_deals = db.query(Deal).filter(Deal.stage == "closed_won").count()
    lost_deals = db.query(Deal).filter(Deal.stage == "closed_lost").count()
    total_closed = won_deals + lost_deals
    win_rate = int((won_deals / total_closed) * 100) if total_closed > 0 else 0

    # Pipeline summary
    pipeline_summary = db.query(
        Deal.stage, 
        func.count(Deal.id).label("count"), 
        func.sum(Deal.value).label("value")
    ).group_by(Deal.stage).all()
    
    # Format summary for template
    summary_dict = {stage: {"count": 0, "value": 0} for stage in ["qualified", "proposal", "negotiation", "closed_won", "closed_lost"]}
    for stage, count, value in pipeline_summary:
        if stage in summary_dict:
            summary_dict[stage] = {"count": count, "value": value or 0}

    # Recent activities (last 10)
    recent_activities = db.query(Activity).order_by(desc(Activity.created_at)).limit(10).all()

    # Upcoming tasks (completed=False)
    upcoming_tasks = db.query(Activity).filter(Activity.completed == False).order_by(Activity.date).limit(10).all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "total_contacts": total_contacts,
        "open_deals_count": open_deals_count,
        "total_pipeline_value": total_pipeline_value,
        "win_rate": win_rate,
        "pipeline_summary": summary_dict,
        "recent_activities": recent_activities,
        "upcoming_tasks": upcoming_tasks
    })
