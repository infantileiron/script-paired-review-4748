from pydantic import BaseModel,Field
from typing import Optional,Literal
class Login(BaseModel):email:str;password:str
class PairInput(BaseModel):
 code:str=Field(min_length=1,max_length=60)
 team:Literal['企业一组','企业二组']
 before:Optional[float]=Field(default=None,ge=0,le=100,allow_inf_nan=False)
 after:Optional[float]=Field(default=None,ge=0,le=100,allow_inf_nan=False)
 note:str=Field(default='',max_length=1000)
class EvaluationInput(BaseModel):
 name:str=Field(min_length=2,max_length=100)
 team:Literal['全部','企业一组','企业二组']='全部'
class AdoptionInput(BaseModel):
 evaluation_id:int=Field(gt=0)
 decision:Literal['继续试点','分组采纳','暂缓采纳']
 note:str=Field(min_length=8,max_length=2000)
class ReviewInput(BaseModel):
 evaluation_id:int=Field(gt=0)
 threshold:float=Field(default=2.0,ge=-100,le=100,allow_inf_nan=False)
 slots:int=Field(default=0,ge=0,le=1000)
class ReviewDispatch(BaseModel):
 count:Optional[int]=Field(default=None,ge=1,le=1000)
 request_key:Optional[str]=Field(default=None,max_length=120)
class ReviewReturn(BaseModel):
 code:str=Field(min_length=1,max_length=60)
 before:Optional[float]=Field(default=None,ge=0,le=100,allow_inf_nan=False)
 after:Optional[float]=Field(default=None,ge=0,le=100,allow_inf_nan=False)
 task_id:Optional[int]=Field(default=None,gt=0)
 source:str=Field(default='',max_length=120)
