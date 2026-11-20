from sqlalchemy import Column,Integer,String,Float,JSON,Text,ForeignKey,Boolean,UniqueConstraint
from src.config.database import Base
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True);email=Column(String(100),unique=True,nullable=False);password=Column(String(200));role=Column(String(20))
class Pair(Base):
 __tablename__='pairs'
 id=Column(Integer,primary_key=True);code=Column(String(60),unique=True,nullable=False);team=Column(String(40));before=Column(Float,nullable=True);after=Column(Float,nullable=True);note=Column(Text,default='')
class Evaluation(Base):
 __tablename__='evaluations'
 id=Column(Integer,primary_key=True);name=Column(String(100));team=Column(String(40));state=Column(String(20),default='queued');result=Column(JSON,nullable=True);error=Column(Text,default='')
class Adoption(Base):
 __tablename__='adoptions'
 id=Column(Integer,primary_key=True);evaluation_id=Column(Integer,ForeignKey('evaluations.id'));decision=Column(String(30));note=Column(Text);status=Column(String(20),default='draft')
class Audit(Base):
 __tablename__='audits'
 id=Column(Integer,primary_key=True);actor=Column(String(100));action=Column(String(200));created=Column(String(40))
class Review(Base):
 """缺测复核：冻结顾问名单与已知分，按缺项取值上下界判断是否达到改善线，并按名额派补查。"""
 __tablename__='reviews'
 id=Column(Integer,primary_key=True)
 evaluation_id=Column(Integer,ForeignKey('evaluations.id'),nullable=False)
 threshold=Column(Float,nullable=False)          # 改善线（平均差值，分）
 slots=Column(Integer,nullable=False,default=0)  # 可派补查名额
 state=Column(String(20),default='open')         # open / concluded / undetermined
 verdict=Column(String(20),nullable=True)        # pass / fail / undetermined
 error=Column(Text,default='')
 result=Column(JSON,nullable=True)               # 最新一次缺测复核结果（含区间与派单）
class ReviewTask(Base):
 """补查派单：每个缺项一条，重试沿用原派单行，不重复占名额。"""
 __tablename__='review_tasks'
 id=Column(Integer,primary_key=True)
 review_id=Column(Integer,ForeignKey('reviews.id'),nullable=False)
 code=Column(String(60),nullable=False)
 team=Column(String(40))
 missing=Column(String(20),nullable=False)        # before / after
 state=Column(String(20),default='dispatched')    # dispatched / returned
 dispatch_key=Column(String(120),nullable=False)  # 幂等键：同一复核同一顾问同一缺项只派一次
 request_key=Column(String(120),nullable=True)    # 批次幂等键：同一请求重试不重复派单
 slot_no=Column(Integer,nullable=True)            # 名额序号：同一复核内唯一，数据库层防超额
 attempts=Column(Integer,default=1)
 created=Column(String(40));updated=Column(String(40));note=Column(Text,default='')
 __table_args__=(UniqueConstraint('review_id','dispatch_key',name='review_tasks_unique_dispatch'),
                 UniqueConstraint('review_id','slot_no',name='review_tasks_unique_slot'))
class PairCorrection(Base):
 """回填记录：保留原始值与来源，晚到回分照收，不改动已结案依据。"""
 __tablename__='pair_corrections'
 id=Column(Integer,primary_key=True)
 review_id=Column(Integer,ForeignKey('reviews.id'),nullable=True)
 pair_id=Column(Integer,ForeignKey('pairs.id'),nullable=False)
 code=Column(String(60));field=Column(String(10))   # before / after
 old_value=Column(Float,nullable=True);new_value=Column(Float,nullable=True)
 source=Column(String(120),default='')
 actor=Column(String(100));created=Column(String(40))
 late=Column(Boolean,default=False)                 # 结案后到达的回分

