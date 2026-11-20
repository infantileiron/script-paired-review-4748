import math,hashlib,json
import numpy as np
from scipy import stats
SEED=1115
ITERATIONS=10000
def evaluate(rows):
 kept=[r for r in rows if r['before'] is not None and r['after'] is not None]
 excluded=[{'code':r['code'],'reason':'缺少前测' if r['before'] is None else '缺少后测'} for r in rows if r not in kept]
 if len(kept)<3:raise ValueError('至少需要3个完整顾问配对；缺失记录不会被补零')
 d=np.array([r['after']-r['before'] for r in kept],dtype=float)
 n=len(d);mean=float(d.mean());sd=float(d.std(ddof=1))
 if sd==0:raise ValueError('所有配对差值相同，t检验标准误为零；请核对样本，勿以无效显著性采纳')
 se=sd/math.sqrt(n);t=mean/se;p=float(stats.t.sf(abs(t),n-1)*2);margin=float(stats.t.ppf(.975,n-1))*se
 if n<=16:
  signs=1-2*((np.arange(2**n)[:,None]>>np.arange(n))&1)
  perm=signs@d/n;permutation_p=float(np.mean(np.abs(perm)>=abs(mean)-1e-12));method='exact';iterations=2**n
 else:
  rng=np.random.default_rng(SEED);extreme=0
  for _ in range(10):
   perm=(rng.choice([-1,1],size=(1000,n))*d).mean(axis=1);extreme+=int(np.count_nonzero(np.abs(perm)>=abs(mean)-1e-12))
  permutation_p=(extreme+1)/(ITERATIONS+1);method='monte-carlo-add-one';iterations=ITERATIONS
 return dict(n=n,excluded=excluded,total=len(rows),before_mean=float(np.mean([r['before'] for r in kept])),after_mean=float(np.mean([r['after'] for r in kept])),difference=mean,sd=sd,t=t,df=n-1,p_value=p,ci=[mean-margin,mean+margin],cohen_dz=mean/sd,permutation_p=permutation_p,permutation_method=method,iterations=iterations,seed=SEED,pairs=kept,checksum=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),warning='配对t检验假设顾问之间独立、差值近似正态；符号翻转假设零假设下差值符号可交换。前后评估同时受到客户结构与季节影响，不能直接解释为话术因果效应。')
