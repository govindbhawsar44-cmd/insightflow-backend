import json
import pandas as pd
import numpy as np
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from database import prisma
from security import get_current_user

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])

class DashboardUpdateRequest(BaseModel):
    layout: list

@router.post("/generate")
async def generate_dashboard(dataset_id: str, user_id: str = Depends(get_current_user)):
    dataset = await prisma.dataset.find_first(where={"id": dataset_id, "userId": user_id})
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        if dataset.name.endswith(".csv"):
            df = pd.read_csv(dataset.url, nrows=100)
        else:
            df = pd.read_excel(dataset.url, nrows=100)
            
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        layout = []
        
        layout.append({"id": "kpi-rows", "type": "kpi", "w": 4, "config": {"title": "Total Rows", "metric": "total_rows"}})
        if numeric_cols:
            layout.append({"id": "kpi-sum", "type": "kpi", "w": 4, "config": {"title": f"Total {numeric_cols[0]}", "metric": "total_sum"}})
            layout.append({"id": "kpi-avg", "type": "kpi", "w": 4, "config": {"title": f"Average {numeric_cols[0]}", "metric": "average"}})
            
        if cat_cols and numeric_cols:
            layout.append({"id": "pie-1", "type": "pie_chart", "w": 4, "config": {"title": f"Breakdown by {cat_cols[0]}"}})
            layout.append({"id": "bar-1", "type": "bar_chart", "w": 8, "config": {"title": f"Top 10 {cat_cols[0]}"}})
            
        if len(numeric_cols) > 1:
            layout.append({"id": "scatter-1", "type": "scatter_plot", "w": 6, "config": {"title": f"{numeric_cols[0]} vs {numeric_cols[1]}"}})
            layout.append({"id": "dist-1", "type": "distribution", "w": 6, "config": {"title": f"Distribution of {numeric_cols[0]}"}})

        existing = await prisma.dashboard.find_unique(where={"datasetId": dataset.id})
        if existing:
            dashboard = await prisma.dashboard.update(
                where={"id": existing.id},
                data={"layout": json.dumps(layout)}
            )
        else:
            dashboard = await prisma.dashboard.create(
                data={
                    "datasetId": dataset.id,
                    "layout": json.dumps(layout)
                }
            )
            
        return {"status": "success", "dashboard": {"id": dashboard.id, "layout": layout}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")

@router.get("/{dataset_id}")
async def get_dashboard(dataset_id: str, user_id: str = Depends(get_current_user)):
    dataset = await prisma.dataset.find_first(where={"id": dataset_id, "userId": user_id})
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    dashboard = await prisma.dashboard.find_unique(where={"datasetId": dataset_id})
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
        
    return {"id": dashboard.id, "layout": json.loads(dashboard.layout) if isinstance(dashboard.layout, str) else dashboard.layout}

@router.put("/{dataset_id}")
async def update_dashboard(dataset_id: str, req: DashboardUpdateRequest, user_id: str = Depends(get_current_user)):
    dataset = await prisma.dataset.find_first(where={"id": dataset_id, "userId": user_id})
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    dashboard = await prisma.dashboard.update(
        where={"datasetId": dataset_id},
        data={"layout": json.dumps(req.layout)}
    )
    return {"status": "success"}
