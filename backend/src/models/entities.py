from sqlalchemy import Column,Integer,String,Float,JSON,Text,ForeignKey
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
