from fastapi import APIRouter, Depends, Request
from foundation.auth import trusted_session
from services.recommendations.models import SavePreferences, RecordEvent, StoreCommand, ProfileResponse, RecommendationResponse, EventResponse, ResetResponse

router=APIRouter(prefix='/internal/v1', tags=['recommendations'])


@router.get('/preferences',response_model=ProfileResponse)
async def preferences(request: Request, owner=Depends(trusted_session)):
    return await request.app.state.recommendations.profile(owner)


@router.post('/preferences',response_model=ProfileResponse)
async def save_preferences(body: SavePreferences, request: Request, owner=Depends(trusted_session)):
    return await request.app.state.recommendations.save(owner,body)


@router.get('/recommendations',response_model=RecommendationResponse)
async def recommendations(request: Request, owner=Depends(trusted_session)):
    return await request.app.state.recommendations.recommend(owner)


@router.post('/recommendation-events',response_model=EventResponse)
async def event(body: RecordEvent, request: Request, owner=Depends(trusted_session)):
    return await request.app.state.recommendations.record(owner,body)


@router.post('/recommendation-reset',response_model=ResetResponse)
async def reset(body: StoreCommand, request: Request, owner=Depends(trusted_session)):
    return await request.app.state.recommendations.reset(owner,body)
