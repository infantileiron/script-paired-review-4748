import random
from src.config.database import Base,engine,Session
from src.models.entities import User,Pair
from src.utils.security import hash_password
def seed():
 Base.metadata.create_all(engine);rng=random.Random(1115)
 with Session() as s:
  for role in ('admin','analyst','viewer'):
   email=role+'@demo.local'
   if not s.query(User).filter_by(email=email).first():s.add(User(email=email,role=role,password=hash_password('Demo123!')))
  for i in range(40):
   code=f'QY-{i+1:03}';before=round(rng.uniform(58,85),1);after=round(min(100,before+rng.gauss(4 if i<20 else 1,5)),1)
   if not s.query(Pair).filter_by(code=code).first():s.add(Pair(code=code,team='企业一组' if i<20 else '企业二组',before=None if i==38 else before,after=None if i==39 else after,note='前后各抽检5次客户沟通的平均得分；窗口均为7日'))
  s.commit();print({'users':s.query(User).count(),'pairs':s.query(Pair).count()})
if __name__=='__main__':seed()
