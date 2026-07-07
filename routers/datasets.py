import os
import uuid
import json
import pandas as pd
import numpy as np
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from database import prisma
from security import get_current_user

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    if not file.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only .csv and .xlsx files are supported")
    
    file_extension = file.filename.split('.')[-1]
    
    existing = await prisma.dataset.find_first(where={"name": file.filename, "userId": user_id})
    if existing:
        raise HTTPException(status_code=400, detail=f"Dataset with name {file.filename} already exists")
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join("uploads", f"{file_id}.{file_extension}")
    
    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")
        
    with open(file_path, "wb") as f:
        f.write(contents)
        
    dataset = await prisma.dataset.create(
        data={
            "name": file.filename,
            "size": len(contents),
            "url": file_path,
            "userId": user_id
        }
    )
    
    return dataset

@router.get("")
async def get_datasets(user_id: str = Depends(get_current_user)):
    datasets = await prisma.dataset.find_many(
        where={"userId": user_id},
        order={"createdAt": "desc"}
    )
    return datasets

@router.get("/recent")
async def get_recent_datasets(user_id: str = Depends(get_current_user)):
    datasets = await prisma.dataset.find_many(
        where={"userId": user_id},
        order={"createdAt": "desc"},
        take=5
    )
    
    formatted = []
    for d in datasets:
        size_mb = round(d.size / (1024 * 1024), 2)
        is_csv = d.name.endswith('.csv')
        formatted.append({
            "id": d.id,
            "name": d.name,
            "meta": f"Updated recently • {size_mb} MB",
            "icon": "description" if is_csv else "table_chart",
            "colorClass": "bg-primary-fixed text-primary" if is_csv else "bg-secondary-fixed text-secondary"
        })
    return formatted

@router.get("/{dataset_id}/preview")
async def preview_dataset(dataset_id: str, user_id: str = Depends(get_current_user)):
    dataset = await prisma.dataset.find_first(where={"id": dataset_id, "userId": user_id})
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        if dataset.name.endswith(".csv"):
            df = pd.read_csv(dataset.url, nrows=10)
        elif dataset.name.endswith(".xlsx"):
            df = pd.read_excel(dataset.url, nrows=10)
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
            
        df.fillna("N/A", inplace=True)
        return {
            "columns": df.columns.tolist(),
            "rows": df.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read dataset: {str(e)}")

@router.get("/{dataset_id}/clean/analyze")
async def analyze_dataset(dataset_id: str, user_id: str = Depends(get_current_user)):
    dataset = await prisma.dataset.find_first(where={"id": dataset_id, "userId": user_id})
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        if dataset.name.endswith(".csv"):
            df = pd.read_csv(dataset.url)
        elif dataset.name.endswith(".xlsx"):
            df = pd.read_excel(dataset.url)
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
            
        issues = []
        score = 100
        
        missing = df.isna().sum()
        total_missing = int(missing.sum())
        if total_missing > 0:
            score -= min(30, (total_missing / df.size) * 100)
            issues.append({
                "title": "Missing Values",
                "description": f"Found {total_missing} missing values across {sum(missing > 0)} columns.",
                "type": "warning"
            })
            
        duplicates = int(df.duplicated().sum())
        if duplicates > 0:
            score -= min(20, (duplicates / len(df)) * 100)
            issues.append({
                "title": "Duplicate Rows",
                "description": f"Found {duplicates} duplicate rows.",
                "type": "error"
            })
            
        outliers_count = 0
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            outliers = ((df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))).sum()
            outliers_count += int(outliers)
            
        if outliers_count > 0:
            score -= min(15, (outliers_count / df.size) * 100)
            issues.append({
                "title": "Outliers Detected",
                "description": f"Found {outliers_count} potential outliers in numeric columns.",
                "type": "warning"
            })
            
        score = max(0, int(score))
        
        sample_df = df.head(100).copy()
        rows = []
        for index, row in sample_df.iterrows():
            row_dict = row.replace({np.nan: None}).to_dict()
            hasError = {}
            for col in sample_df.columns:
                if pd.isna(row[col]):
                    hasError[col] = True
            row_dict['id'] = str(index)
            row_dict['hasError'] = hasError
            rows.append(row_dict)
            
        if dataset.qualityScore != score:
            await prisma.dataset.update(
                where={"id": dataset.id},
                data={"qualityScore": score}
            )
            
        return {
            "columns": df.columns.tolist(),
            "rows": rows,
            "issues": issues,
            "qualityScore": score,
            "totalRows": len(df),
            "originalUrl": dataset.originalUrl
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/{dataset_id}/clean/apply")
async def apply_cleaning(dataset_id: str, user_id: str = Depends(get_current_user)):
    dataset = await prisma.dataset.find_first(where={"id": dataset_id, "userId": user_id})
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        if dataset.name.endswith(".csv"):
            df = pd.read_csv(dataset.url)
        else:
            df = pd.read_excel(dataset.url)
            
        original_url = dataset.originalUrl if dataset.originalUrl else dataset.url
        if not dataset.originalUrl:
            new_cleaned_path = dataset.url.replace(".csv", "_cleaned.csv").replace(".xlsx", "_cleaned.xlsx")
        else:
            new_cleaned_path = dataset.url
            
        df.drop_duplicates(inplace=True)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if not df[col].empty and not pd.isna(df[col].median()):
                df[col] = df[col].fillna(df[col].median())
        cat_cols = df.select_dtypes(exclude=[np.number]).columns
        for col in cat_cols:
            df[col] = df[col].fillna("Unknown")
            
        if dataset.name.endswith(".csv"):
            df.to_csv(new_cleaned_path, index=False)
        else:
            df.to_excel(new_cleaned_path, index=False)
            
        history = [
            {"action": "Removed duplicates", "timestamp": str(pd.Timestamp.now())},
            {"action": "Imputed missing values", "timestamp": str(pd.Timestamp.now())},
        ]
            
        await prisma.dataset.update(
            where={"id": dataset.id},
            data={
                "url": new_cleaned_path,
                "originalUrl": original_url,
                "qualityScore": 100,
                "cleaningHistory": json.dumps(history)
            }
        )
        return {"status": "success", "message": "Dataset cleaned successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleaning failed: {str(e)}")

@router.post("/{dataset_id}/clean/undo")
async def undo_cleaning(dataset_id: str, user_id: str = Depends(get_current_user)):
    dataset = await prisma.dataset.find_first(where={"id": dataset_id, "userId": user_id})
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    if not dataset.originalUrl:
        raise HTTPException(status_code=400, detail="No original version to revert to")
        
    await prisma.dataset.update(
        where={"id": dataset.id},
        data={
            "url": dataset.originalUrl,
            "originalUrl": None,
            "qualityScore": None,
            "cleaningHistory": None
        }
    )
    return {"status": "success", "message": "Dataset reverted to original state"}
