"""Lab 15.1: JWT tenant identity, tenant-scoped CRUD, RBAC, atomic fixed-window counters."""
from contextlib import asynccontextmanager
from datetime import datetime,timezone,timedelta
import os,time,secrets,hashlib,hmac
from typing import Literal
import jwt
from fastapi import FastAPI,Depends,HTTPException,Request,Response
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from pydantic import BaseModel,Field,ConfigDict
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from core import client

ISSUER='nosql-coursework';AUDIENCE='task-api'

def password_hash(password,salt=None):
    salt=salt or secrets.token_hex(16)
    value=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    return salt+':'+value

def check_password(password,stored):
    try:return hmac.compare_digest(password_hash(password,stored.split(':')[0]),stored)
    except (ValueError,TypeError):return False

def seed_users(db):
    password=os.environ['DEMO_PASSWORD']
    for username,tenant,role in [('alice','tenant-a','user'),('bob','tenant-a','user'),('admin-a','tenant-a','admin'),('carol','tenant-b','user'),('admin-b','tenant-b','admin'),('rateuser','tenant-rate','user')]:
        db.users.update_one({'_id':username},{'$setOnInsert':{'tenant_id':tenant,'role':role,'password_hash':password_hash(password)}},upsert=True)

def rate_check(db,identity,limit=20,window=60):
    now=time.time();bucket=int(now//window);key=f'{identity}:{bucket}'
    update={'$inc':{'count':1},'$setOnInsert':{'expires_at':datetime.fromtimestamp((bucket+2)*window,timezone.utc)}}
    try:doc=db.rate_limits.find_one_and_update({'_id':key},update,upsert=True,return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        doc=db.rate_limits.find_one_and_update({'_id':key},{'$inc':{'count':1}},return_document=ReturnDocument.AFTER)
    if doc['count']>limit:raise HTTPException(429,'Rate limit exceeded',headers={'Retry-After':str(max(1,int((bucket+1)*window-now)))})

@asynccontextmanager
async def lifespan(app):
    secret=os.environ.get('JWT_SECRET','')
    if len(secret)<32:raise RuntimeError('Run SETUP.ps1 to create a private JWT signing secret.')
    c=client();c.admin.command('ping');db=c.exercise15_api
    db.tasks.create_index([('tenant_id',1),('created_at',-1)])
    db.tasks.create_index([('tenant_id',1),('owner_id',1),('created_at',-1)])
    db.rate_limits.create_index('expires_at',expireAfterSeconds=0)
    seed_users(db);app.state.db=db
    try:yield
    finally:c.close()

app=FastAPI(title='Exercise 15 - Tenant Task API',version='1.0',lifespan=lifespan)
bearer=HTTPBearer(auto_error=False)

def identity(request:Request,auth:HTTPAuthorizationCredentials=Depends(bearer)):
    if not auth:raise HTTPException(401,'Bearer token required')
    try:
        claims=jwt.decode(auth.credentials,os.environ['JWT_SECRET'],algorithms=['HS256'],issuer=ISSUER,audience=AUDIENCE,options={'require':['exp','iat','sub','tenant_id']})
        u=request.app.state.db.users.find_one({'_id':claims['sub'],'tenant_id':claims['tenant_id']})
        if not u or u['role'] not in ('admin','user'):raise ValueError('Unknown identity')
    except (jwt.InvalidTokenError,ValueError,KeyError):raise HTTPException(401,'Invalid or expired token')
    rate_check(request.app.state.db,u['tenant_id']+':'+u['_id'])
    return u

def scoped(user,task_id=None):
    query={'tenant_id':user['tenant_id']}
    if user['role']!='admin':query['owner_id']=user['_id']
    if task_id is not None:
        if not ObjectId.is_valid(task_id):raise HTTPException(404,'Task not found')
        query['_id']=ObjectId(task_id)
    return query

def render(doc):
    return {**{k:v for k,v in doc.items() if k!='_id'},'id':str(doc['_id'])}

class Login(BaseModel):
    model_config=ConfigDict(extra='forbid')
    username:str=Field(min_length=1,max_length=100)
    password:str=Field(min_length=1,max_length=300)
class TaskCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str=Field(min_length=1,max_length=200)
    description:str=Field(default='',max_length=4000)
    priority:Literal['low','medium','high']='medium'
class TaskUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str|None=Field(default=None,min_length=1,max_length=200)
    description:str|None=Field(default=None,max_length=4000)
    priority:Literal['low','medium','high']|None=None
    status:Literal['open','in_progress','completed']|None=None

@app.get('/health')
def health(request:Request):
    request.app.state.db.command('ping');return {'status':'ok'}
@app.post('/auth/token')
def login(data:Login,request:Request):
    db=request.app.state.db;rate_check(db,'login:'+data.username,limit=15)
    u=db.users.find_one({'_id':data.username})
    if not u or not check_password(data.password,u['password_hash']):raise HTTPException(401,'Invalid credentials')
    now=datetime.now(timezone.utc)
    claims={'sub':u['_id'],'tenant_id':u['tenant_id'],'iss':ISSUER,'aud':AUDIENCE,'iat':now,'exp':now+timedelta(minutes=30)}
    return {'access_token':jwt.encode(claims,os.environ['JWT_SECRET'],algorithm='HS256'),'token_type':'bearer','expires_in':1800}
@app.post('/tasks',status_code=201)
def create_task(data:TaskCreate,request:Request,user=Depends(identity)):
    now=datetime.now(timezone.utc);doc={**data.model_dump(),'tenant_id':user['tenant_id'],'owner_id':user['_id'],'status':'open','created_at':now,'updated_at':now}
    doc['_id']=request.app.state.db.tasks.insert_one(doc).inserted_id;return render(doc)
@app.get('/tasks')
def list_tasks(request:Request,limit:int=50,user=Depends(identity)):
    return [render(x) for x in request.app.state.db.tasks.find(scoped(user)).sort('created_at',-1).limit(max(1,min(limit,100)))]
@app.get('/tasks/{task_id}')
def get_task(task_id:str,request:Request,user=Depends(identity)):
    doc=request.app.state.db.tasks.find_one(scoped(user,task_id))
    if not doc:raise HTTPException(404,'Task not found')
    return render(doc)
@app.patch('/tasks/{task_id}')
def update_task(task_id:str,data:TaskUpdate,request:Request,user=Depends(identity)):
    values=data.model_dump(exclude_unset=True)
    if not values or any(v is None for v in values.values()):raise HTTPException(422,'Provide non-null task fields')
    values['updated_at']=datetime.now(timezone.utc)
    doc=request.app.state.db.tasks.find_one_and_update(scoped(user,task_id),{'$set':values},return_document=ReturnDocument.AFTER)
    if not doc:raise HTTPException(404,'Task not found')
    return render(doc)
@app.delete('/tasks/{task_id}',status_code=204)
def delete_task(task_id:str,request:Request,user=Depends(identity)):
    result=request.app.state.db.tasks.delete_one(scoped(user,task_id))
    if not result.deleted_count:raise HTTPException(404,'Task not found')
    return Response(status_code=204)
