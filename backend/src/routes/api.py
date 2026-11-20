import os,json
import redis
from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy.exc import IntegrityError
from src.config.database import db
from src.models.entities import User,Pair,Evaluation,Adoption,Audit,Review
from src.schemas.business import Login,PairInput,EvaluationInput,AdoptionInput,ReviewInput,ReviewDispatch,ReviewReturn
from src.middlewares.auth import current,editor,admin
from src.utils.security import verify,token
from src.services.business import audit,dump
from src.services import review as review_service
from src.controllers.business import ensure_evaluation
router=APIRouter()
@router.post('/auth/login')
def login(data:Login,s=Depends(db)):
 u=s.query(User).filter_by(email=data.email).first()
 if not u or not verify(data.password,u.password):raise HTTPException(401,'账号或密码错误')
 return {'token':token(u),'user':dump(u)}
@router.get('/me')
def me(u=Depends(current)):return dump(u)
@router.get('/pairs')
def pairs(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Pair).order_by(Pair.id).all()]
@router.post('/pairs')
def create_pair(data:PairInput,u=Depends(editor),s=Depends(db)):
 r=Pair(**data.model_dump());s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'顾问编号已存在，每位顾问仅保留一组前后测')
 audit(s,u,'录入顾问配对 '+r.code);review_service.sync_pair_backfill(s,r,u);return dump(r)
@router.put('/pairs/{i}')
def edit_pair(i:int,data:PairInput,u=Depends(editor),s=Depends(db)):
 r=s.get(Pair,i)
 if not r:raise HTTPException(404,'配对记录不存在')
 for k,v in data.model_dump().items():setattr(r,k,v)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'顾问编号重复')
 audit(s,u,'修订配对 '+str(i));review_service.sync_pair_backfill(s,r,u);return dump(r)
@router.get('/evaluations')
def evaluations(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Evaluation).order_by(Evaluation.id.desc()).all()]
@router.post('/evaluations')
def evaluate(data:EvaluationInput,u=Depends(editor),s=Depends(db)):
 rows=[dump(r) for r in s.query(Pair).order_by(Pair.id).all() if data.team=='全部' or r.team==data.team]
 r=Evaluation(**data.model_dump(),result={'snapshot':rows});s.add(r);s.commit()
 try:redis.Redis.from_url(os.environ['REDIS_URL']).rpush('paired:evaluations',r.id)
 except redis.RedisError:r.state='failed';r.error='队列暂不可用，请稍后重新提交';s.commit();raise HTTPException(503,r.error)
 audit(s,u,'提交评估 '+str(r.id));return dump(r)
@router.get('/evaluations/{i}')
def detail(i:int,u=Depends(current),s=Depends(db)):return dump(ensure_evaluation(s,i))
@router.get('/evaluations/{i}/export')
def export(i:int,u=Depends(current),s=Depends(db)):
 r=ensure_evaluation(s,i)
 if r.state!='done':raise HTTPException(409,'仅成功评估可导出')
 return Response(json.dumps(dump(r),ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="script-paired-{i}.json"'})
@router.get('/reviews')
def reviews(u=Depends(current),s=Depends(db),evaluation_id:int|None=None):
 q=s.query(Review)
 if evaluation_id is not None:q=q.filter_by(evaluation_id=evaluation_id)
 return [dump(r) for r in q.order_by(Review.id.desc()).all()]
@router.get('/reviews/{i}')
def review_detail(i:int,u=Depends(current),s=Depends(db)):
 r=s.get(Review,i)
 if not r:raise HTTPException(404,'缺测复核不存在')
 return dump(r)
@router.post('/reviews')
def create_review(data:ReviewInput,u=Depends(editor),s=Depends(db)):
 e=ensure_evaluation(s,data.evaluation_id)
 if e.state!='done':raise HTTPException(409,'评估完成后才能建立缺测复核')
 r=review_service.create(s,e,data.threshold,data.slots,u)
 audit(s,u,'建立缺测复核 '+str(r.id))
 return dump(r)
@router.post('/reviews/{i}/dispatch')
def dispatch_review(i:int,data:ReviewDispatch|None=None,u=Depends(editor),s=Depends(db)):
 r=review_service.lock(s,i)
 payload=data or ReviewDispatch()
 try:result=review_service.dispatch(s,r,payload.count,u,payload.request_key)
 except HTTPException:
  s.rollback();raise
 audit(s,u,'缺测复核派补查 '+str(i))
 return {'id':r.id,'state':r.state,'verdict':r.verdict,'result':result}
@router.post('/reviews/{i}/tasks/{t}/retry')
def retry_review(i:int,t:int,u=Depends(editor),s=Depends(db)):
 r=review_service.lock(s,i)
 try:result=review_service.retry(s,r,t,u)
 except HTTPException:
  s.rollback();raise
 audit(s,u,f'缺测复核重试派单 {i}/{t}')
 return {'id':r.id,'state':r.state,'verdict':r.verdict,'result':result}
@router.post('/reviews/{i}/recompute')
def recompute_review(i:int,u=Depends(editor),s=Depends(db)):
 r=review_service.lock(s,i)
 review_service.recompute(s,r)
 audit(s,u,'缺测复核重算区间 '+str(i))
 return dump(r)
@router.post('/reviews/{i}/returns')
def review_returns(i:int,data:ReviewReturn,u=Depends(editor),s=Depends(db)):
 r=review_service.lock(s,i)
 try:result=review_service.record_return(s,r,u,data.code,before=data.before,after=data.after,task_id=data.task_id,source=data.source)
 except HTTPException:
  s.rollback();raise
 audit(s,u,f'缺测复核回分 {i} {data.code}')
 return {'id':r.id,'state':r.state,'verdict':r.verdict,'result':result}
@router.get('/adoptions')
def adoptions(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Adoption).order_by(Adoption.id.desc()).all()]
@router.post('/adoptions')
def adoption(data:AdoptionInput,u=Depends(editor),s=Depends(db)):
 if ensure_evaluation(s,data.evaluation_id).state!='done':raise HTTPException(409,'评估完成后才能起草采纳意见')
 r=Adoption(**data.model_dump());s.add(r);s.commit();audit(s,u,'起草采纳意见 '+str(r.id));return dump(r)
@router.post('/adoptions/{i}/approve')
def approve(i:int,u=Depends(admin),s=Depends(db)):
 r=s.get(Adoption,i)
 if not r:raise HTTPException(404,'采纳意见不存在')
 if r.status!='draft':raise HTTPException(409,'已签核意见不可重复签核')
 r.status='approved';s.commit();audit(s,u,'签核意见 '+str(i));return dump(r)
@router.get('/audits')
def audits(u=Depends(admin),s=Depends(db)):return [dump(r) for r in s.query(Audit).order_by(Audit.id.desc()).limit(100)]
