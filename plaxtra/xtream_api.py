from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .xtream import XtreamClient, XtreamConfig

router = APIRouter(prefix='/api/admin/xtream', tags=['xtream'])

class XtreamConnection(BaseModel):
    host: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    https: bool = True

def client(data: XtreamConnection):
    return XtreamClient(XtreamConfig(**data.model_dump()))

@router.post('/test')
def test_connection(data: XtreamConnection):
    try:
        info = client(data).server_info()
        return {'ok': True, 'server_info': info}
    except Exception as exc:
        raise HTTPException(400, f'Xtream connection failed: {exc}')

@router.post('/preview')
def preview(data: XtreamConnection):
    try:
        c = client(data)
        return {
            'ok': True,
            'live_categories': c.live_categories(),
            'vod_categories': c.vod_categories(),
            'series_categories': c.series_categories(),
        }
    except Exception as exc:
        raise HTTPException(400, f'Xtream connection failed: {exc}')
