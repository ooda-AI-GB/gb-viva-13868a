from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import CompanyIntel
import app.routes as routes_module
import os
from pydantic import BaseModel
from google import genai

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

class IntelRequest(BaseModel):
    company_name: str
    analysis_type: str

@router.get("/intel", response_class=HTMLResponse)
async def intel_dashboard(
    request: Request,
    user=Depends(routes_module.get_current_user),
    subscription=Depends(routes_module.get_active_subscription),
    db: Session = Depends(get_db)
):
    analyses = db.query(CompanyIntel).order_by(desc(CompanyIntel.generated_at)).all()
    return templates.TemplateResponse("intel/dashboard.html", {
        "request": request,
        "analyses": analyses,
        "user": user
    })

@router.get("/intel/{id}", response_class=HTMLResponse)
async def view_analysis(
    request: Request,
    id: int,
    user=Depends(routes_module.get_current_user),
    subscription=Depends(routes_module.get_active_subscription),
    db: Session = Depends(get_db)
):
    analysis = db.query(CompanyIntel).filter(CompanyIntel.id == id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return templates.TemplateResponse("intel/analysis.html", {
        "request": request, 
        "analysis": analysis,
        "user": user
    })

@router.post("/api/intel/analyze")
async def analyze_company(
    request: Request,
    data: IntelRequest,
    user=Depends(routes_module.get_current_user),
    subscription=Depends(routes_module.get_active_subscription),
    db: Session = Depends(get_db)
):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return JSONResponse(status_code=500, content={"error": "Google API Key not set"})
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"Analyze the company '{data.company_name}' using a {data.analysis_type.upper()} analysis. Provide a structured and detailed report."
    
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        content = response.text
        
        intel = CompanyIntel(
            company_name=data.company_name,
            analysis_type=data.analysis_type,
            content=content,
            model_used="gemini-2.5-flash",
            requested_by=str(user.email)
        )
        db.add(intel)
        db.commit()
        db.refresh(intel)
        
        return JSONResponse({"id": intel.id, "status": "success"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
