import uuid
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from database import prisma
from security import get_current_user
from routers.analytics import generate_analytics, AnalyticsRequest

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/")
async def list_reports(user_id: str = Depends(get_current_user)):
    reports = await prisma.report.find_many(where={"userId": user_id}, order={"createdAt": "desc"})
    return reports

@router.post("/generate")
async def generate_report(dataset_id: str, user_id: str = Depends(get_current_user)):
    dataset = await prisma.dataset.find_first(where={"id": dataset_id, "userId": user_id})
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        # Re-use analytics engine to get core intelligence
        req = AnalyticsRequest(datasetId=dataset_id)
        analytics_data = await generate_analytics(req, user_id)
        
        kpis = analytics_data["kpis"]
        exec_summary = analytics_data["executive_summary"]
        
        # Build Power-BI Style Business Report
        report_content = {
            "title": f"Business Intelligence Report: {dataset.name}",
            "sections": [
                {
                    "type": "executive_summary",
                    "title": "Executive Summary",
                    "content": f"The dataset encompasses {kpis['total_orders']} recorded transactions across {kpis['total_customers']} customers. Overall revenue reached ${kpis['total_sales']:.2f} with a profit margin of {kpis['profit_margin']:.1f}%. The best performing region was {exec_summary['top_region']}."
                },
                {
                    "type": "key_insights",
                    "title": "Key Insights & Trends",
                    "bullets": analytics_data["ai_insights"]
                },
                {
                    "type": "forecast",
                    "title": "Predictive Forecast",
                    "content": f"Based on the {exec_summary['growth_trend'].lower()} trend, we anticipate a {kpis['growth_pct']:.1f}% adjustment in the upcoming quarter. Seasonal variations in the {exec_summary['best_category']} category may drive a surge in Q4."
                },
                {
                    "type": "risks",
                    "title": "Business Risks",
                    "content": "Supply chain dependencies in underperforming regions pose a slight inventory risk. Furthermore, maintaining profit margins requires minimizing discount allocations on negative-profit transactions."
                },
                {
                    "type": "recommendations",
                    "title": "Strategic Recommendations",
                    "bullets": [
                        f"Double down on marketing spend in {exec_summary['top_region']}.",
                        f"Investigate customer acquisition strategies similar to those used for {exec_summary['highest_customer']}.",
                        "Audit transactions with negative profit margins to eliminate inefficient discounts."
                    ]
                }
            ]
        }
        
        # Save Report
        new_report = await prisma.report.create(
            data={
                "title": f"AI Report: {dataset.name}",
                "type": "Power BI Style Analysis",
                "datasetId": dataset_id,
                "content": str(report_content),
                "userId": user_id
            }
        )
        return new_report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@router.get("/{report_id}")
async def get_report(report_id: str, user_id: str = Depends(get_current_user)):
    report = await prisma.report.find_first(where={"id": report_id, "userId": user_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
