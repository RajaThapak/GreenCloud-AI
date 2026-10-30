# app/main.py
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.errors import ApiError
from .api.routers import admin, auth, insights, workloads
from .config import settings
from .scheduler.models import NoEligibleInstance, NoFeasiblePlan, SchedulerError
from .api.routes import api

app = FastAPI(title="GreenCloud AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ApiError)
async def api_error(request: Request, error: ApiError):
    return JSONResponse(status_code=error.status, content={"detail": error.detail, "code": error.code})


@app.exception_handler(SchedulerError)
async def scheduler_error(request: Request, error: SchedulerError):
    code = "no_eligible_instance" if isinstance(error, NoEligibleInstance) else (
        "no_feasible_plan" if isinstance(error, NoFeasiblePlan) else "scheduler_error"
    )
    body = {"detail": str(error), "code": code}
    if isinstance(error, NoFeasiblePlan) and error.earliest_finish:
        body["earliest_finish"] = error.earliest_finish.isoformat()
    return JSONResponse(status_code=422, content=body)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    fields = {}
    for item in error.errors():
        location = [str(value) for value in item["loc"] if value not in ("body", "query", "path")]
        fields[".".join(location) or "body"] = item["msg"].removeprefix("Value error, ")
    return JSONResponse(status_code=422, content={
        "detail": "Please check the highlighted fields.", "code": "validation_error", "fields": fields,
    })

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(api)
for router in (auth.router, workloads.router, insights.router, admin.router):
    app.include_router(router)