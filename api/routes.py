from fastapi import APIRouter
from api.endpoints import auth_routes, feedback_link_routes, users_routes, audio_routes ,models_routes, report_routes, feedback_email_routes, transcribe_routes, anomaly_routes, statistics_routes

api_router = APIRouter() 
api_router.include_router(auth_routes.router, tags=["Auth"]) 
api_router.include_router(users_routes.router, tags=["Users"]) 
api_router.include_router(audio_routes.router, tags=["Audio files"]) 
api_router.include_router(feedback_link_routes.router, tags=["Feedback with link"])
api_router.include_router(feedback_email_routes.router, tags=["Feedback with Email"])
api_router.include_router(models_routes.router, tags=["Model"])
api_router.include_router(report_routes.router, tags=["Report"])
api_router.include_router(transcribe_routes.router, tags=["Transcribe"])
api_router.include_router(anomaly_routes.router, tags=["Anomaly Detection"])
api_router.include_router(statistics_routes.router, tags=["Statistics Routes"])