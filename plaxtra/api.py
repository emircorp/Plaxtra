from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .db import SessionLocal, User, Movie, Series, Season, Episode, Channel, WatchProgress, Favorite, Setting, AuditLog
from .security import hash_password, verify_password

router=APIRouter(prefix="/api")
def db_dep():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def current_user(request: Request, db: Session=Depends(db_dep)):
    uid=request.session.get("user_id")
    if not uid: raise HTTPException(401,"Login required")
    user=db.get(User,uid)
    if not user or not user.active: raise HTTPException(401,"Invalid session")
    return user

def admin(user=Depends(current_user)):
    if user.role!="admin": raise HTTPException(403,"Admin access required")
    return user

class Credentials(BaseModel): username:str; password:str
class Progress(BaseModel): media_type:str; media_id:int; position:float; duration:float=0
class FavoriteIn(BaseModel): media_type:str; media_id:int
class MovieIn(BaseModel): title:str; synopsis:str=""; year:int|None=None; genre:str=""; poster_url:str=""; backdrop_url:str=""; stream_url:str=""; duration:int|None=None; featured:bool=False
class ChannelIn(BaseModel): name:str; stream_url:str; group_name:str="General"; logo_url:str=""; epg_id:str=""; number:int|None=None

@router.get('/health')
def health(): return {'status':'ok','service':'plaxtra'}

@router.get('/setup/status')
def setup_status(db:Session=Depends(db_dep)): return {'setup_required':db.query(User).count()==0}

@router.post('/setup')
def setup(c:Credentials,db:Session=Depends(db_dep)):
    if db.query(User).count(): raise HTTPException(409,'Setup already completed')
    if len(c.password)<8: raise HTTPException(400,'Password must be at least 8 characters')
    u=User(username=c.username.strip(),password_hash=hash_password(c.password),role='admin')
    db.add(u); db.commit(); return {'ok':True}

@router.post('/auth/login')
def login(c:Credentials,request:Request,db:Session=Depends(db_dep)):
    u=db.query(User).filter_by(username=c.username.strip()).first()
    if not u or not u.active or not verify_password(c.password,u.password_hash): raise HTTPException(401,'Invalid credentials')
    request.session['user_id']=u.id; return {'username':u.username,'role':u.role}

@router.post('/auth/logout')
def logout(request:Request): request.session.clear(); return {'ok':True}

@router.get('/auth/me')
def me(u=Depends(current_user)): return {'id':u.id,'username':u.username,'role':u.role}

@router.get('/catalog')
def catalog(db:Session=Depends(db_dep)):
    return {'movies':[{'id':m.id,'title':m.title,'year':m.year,'genre':m.genre,'poster_url':m.poster_url,'backdrop_url':m.backdrop_url,'stream_url':m.stream_url,'featured':m.featured} for m in db.query(Movie).filter_by(active=True).all()], 'series':[{'id':s.id,'title':s.title,'year':s.year,'genre':s.genre,'poster_url':s.poster_url} for s in db.query(Series).filter_by(active=True).all()]}

@router.get('/movies')
def movies(db:Session=Depends(db_dep)): return catalog(db)['movies']
@router.post('/admin/movies')
def add_movie(m:MovieIn,db:Session=Depends(db_dep),u=Depends(admin)):
    x=Movie(**m.model_dump()); db.add(x); db.add(AuditLog(actor=u.username,action='create_movie',target=m.title)); db.commit(); return {'id':x.id}

@router.get('/live')
def live(db:Session=Depends(db_dep)): return [{'id':c.id,'name':c.name,'group':c.group_name,'logo_url':c.logo_url,'stream_url':c.stream_url,'epg_id':c.epg_id,'number':c.number} for c in db.query(Channel).filter_by(active=True).order_by(Channel.number).all()]
@router.post('/admin/channels')
def add_channel(c:ChannelIn,db:Session=Depends(db_dep),u=Depends(admin)):
    x=Channel(**c.model_dump()); db.add(x); db.add(AuditLog(actor=u.username,action='create_channel',target=c.name)); db.commit(); return {'id':x.id}

@router.post('/progress')
def progress(p:Progress,u=Depends(current_user),db:Session=Depends(db_dep)):
    x=db.query(WatchProgress).filter_by(user_id=u.id,media_type=p.media_type,media_id=p.media_id).first()
    if not x: x=WatchProgress(user_id=u.id,media_type=p.media_type,media_id=p.media_id); db.add(x)
    x.position=max(0,p.position); x.duration=max(0,p.duration); x.updated_at=datetime.utcnow(); db.commit(); return {'ok':True}

@router.get('/favorites')
def favorites(u=Depends(current_user),db:Session=Depends(db_dep)): return [{'media_type':x.media_type,'media_id':x.media_id} for x in db.query(Favorite).filter_by(user_id=u.id).all()]
@router.post('/favorites/toggle')
def favorite(f:FavoriteIn,u=Depends(current_user),db:Session=Depends(db_dep)):
    x=db.query(Favorite).filter_by(user_id=u.id,media_type=f.media_type,media_id=f.media_id).first()
    if x: db.delete(x); state=False
    else: db.add(Favorite(user_id=u.id,**f.model_dump())); state=True
    db.commit(); return {'favorite':state}

@router.get('/admin/settings')
def settings(db:Session=Depends(db_dep),u=Depends(admin)): return {x.key:x.value for x in db.query(Setting).all()}
@router.put('/admin/settings/{key}')
def setting(key:str,value:str,db:Session=Depends(db_dep),u=Depends(admin)):
    x=db.query(Setting).filter_by(key=key).first() or Setting(key=key); x.value=value; db.add(x); db.commit(); return {'ok':True}

@router.get('/admin/audit')
def audit(db:Session=Depends(db_dep),u=Depends(admin)): return [{'actor':x.actor,'action':x.action,'target':x.target,'created_at':x.created_at} for x in db.query(AuditLog).order_by(AuditLog.id.desc()).limit(200).all()]
