from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import prisma
from routers import auth, datasets, analytics, dashboards, reports

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        print("Attempting to connect to Prisma database...")
        await prisma.connect()
        print("Successfully connected to Prisma database.")
        
        # Ensure mock user exists for portfolio demo
        mock_user = await prisma.user.find_unique(where={"id": "user_mock"})
        if not mock_user:
            await prisma.user.create(
                data={
                    "id": "user_mock",
                    "email": "mock-demo-unique@insightiq.com",
                    "name": "Demo User",
                    "passwordHash": "mock_hash"
                }
            )
            print("Created mock user for portfolio demo.")
    except Exception as e:
        print(f"CRITICAL ERROR connecting to database: {e}")
        # Don't crash Uvicorn; let it start so we can see the logs
    yield
    # Shutdown
    if prisma.is_connected():
        await prisma.disconnect()

app = FastAPI(title="InsightFlow API", lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(analytics.router)
app.include_router(dashboards.router)
app.include_router(reports.router)

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
