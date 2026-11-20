import os,time,json,logging
from pathlib import Path
import redis
from src.config.database import Session
from src.models.entities import Evaluation
from src.services.analysis import evaluate
from src.services import review as review_service
def recover():
 """单worker启动恢复：queued/running 任务重新排队；未结案的缺测复核按已收回到分重算。"""
 r=redis.Redis.from_url(os.environ['REDIS_URL'])
 with Session() as s:
  for pending in s.query(Evaluation).filter(Evaluation.state.in_(['queued','running'])).all():
   pending.state='queued';r.rpush('paired:evaluations',pending.id)
  s.commit()
  review_service.recover_open(s)
 return r
def main():
 r=recover()
 while True:
  Path('/tmp/heartbeat').touch()
  try:
   item=r.blpop('paired:evaluations',timeout=3)
   if not item:continue
   with Session() as s:
    row=s.get(Evaluation,int(item[1]))
    if not row or row.state!='queued':continue
    snapshot=row.result['snapshot'];row.state='running';s.commit()
    try:
     row.result={**evaluate(snapshot),'snapshot':snapshot};row.state='done'
     Path('/artifacts/'+str(row.id)+'.json').write_text(json.dumps(row.result,ensure_ascii=False))
    except Exception as e:row.state='failed';row.error=str(e)
    s.commit()
  except Exception:logging.exception('worker');time.sleep(2)
if __name__=='__main__':main()
