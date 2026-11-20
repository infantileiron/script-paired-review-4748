from fastapi import HTTPException
from src.models.entities import Evaluation
from src.services.business import dump
def ensure_evaluation(s,i):
 row=s.get(Evaluation,i)
 if not row:raise HTTPException(404,'评估任务不存在')
 return row
