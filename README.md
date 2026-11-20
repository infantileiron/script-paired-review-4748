# 清音 · 话术切换配对评估

为客户成功团队核对同一顾问更换续约话术前后的抽检得分，将样本完整性、统计证据和业务采纳分开记录。

## 场景与模块

清音客户成功有两组共40位顾问。当前组长导出 `清音_续约抽检_20261115.xlsx`，人工匹配两周得分，分析师计算差值后把结论贴到周会纪要。痛点是漏配对被补零、均值改善被误当因果、采纳意见缺乏证据版本。上游是沟通质量抽检；本项目替代配对核对、统计和采纳留痕；下游是组长制定下一周话术试点范围。

四个业务模块：配对样本（录入/修订）、排除核对、效应评估（后台任务/冻结结果）、采纳意见（起草/签核）。三类业务实体是 Pair、Evaluation、Adoption；另有用户和审计记录。已有报告不会随原始样本修订而改变。

|角色|页面与权限|典型动作|
|---|---|---|
|admin|全部，独占审计和签核|签核采纳意见|
|analyst|业务读写、计算、导出|补录缺失后新建评估|
|viewer|全部业务只读、导出|下载冻结结果；后端拒绝写操作|

## 启动

```sh
cp .env.example .env
docker compose config --quiet
docker compose up -d --build
docker compose exec -T backend python -m scripts.seed_demo
```

前端 [localhost:18214](http://localhost:18214)，后端 [localhost:19214/docs](http://localhost:19214/docs)，PostgreSQL映射17714。种子账号为 `admin@demo.local` / `analyst@demo.local` / `viewer@demo.local`，密码均 `Demo123!`。启动 `SEED_DEMO=true` 自动执行一次种子；再次执行不增加相同顾问或覆盖人工修订。演示包括40顾问、2个业务组、2个不完整配对。

## 一天的操作剧本

1. 08:50 viewer 查看QY-001至QY-040的前后测。
2. 09:00 analyst 进入排除核对，检查QY-039缺前测和QY-040缺后测。
3. 09:10 在配对样本补录 `QY-041`、企业一组、前测70、后测77。
4. 09:20 修订时填写记录ID和完整字段，并说明两次抽检都用7日窗口。
5. 09:30 创建“11月续约话术配对复核”，选择全部或一个业务组。
6. 09:40 worker完成计算，点击刷新，核对差值、95%CI与两种p值。
7. 10:00 analyst 在采纳意见选择该评估，写明客户结构和限制，起草“继续试点”。
8. 10:10 admin登录并签核；10:20 viewer 下载 `script-paired-<id>.json`。

## 计算口径

输入是同一顾问的前后抽检平均分（0–100），一位顾问只允许一个唯一编号。缺任一侧时整对排除，不补零。至少3个完整配对，差值标准差必须大于零。令 d=后测−前测，t=mean(d)/(sd(d)/sqrt(n))，自由度n−1，双侧p与95%t区间；Cohen dz=mean(d)/sd(d)。配对t假定顾问之间独立，差值近似正态。

符号翻转以abs(mean(d))为统计量，≤16对穷举2^n种符号，取不小于观察统计量的占比；更大样本固定numpy seed=1115、10000次抽样，p=(extreme+1)/(10000+1)，比较时用1e−12容差。零假设下需差值符号可交换。前后观测可能受客户结构/季节影响；统计结果不会直接触发话术发布。

提交任务时冻结全部输入，worker保存完整配对、排除原因、checksum、seed和计算次数。无效输入返回422；重复编号409；样本不足/零方差的任务置failed，提示修复后重新提交；队列故障返回503。单worker启动时恢复queued/running任务。

## 工程与本地开发

Python3.11/FastAPI/SQLAlchemy/SciPy/NumPy/PyJWT、原生ES modules/CSS、Nginx、PostgreSQL16、Redis7。五个服务均有健康检查；backend等待数据库/Redis，worker还等backend，frontend等backend。数据库、Redis、产物用命名卷。Nginx的 `/api/` 转发到后端根路由。只有数据库、后端和前端映射宿主端口。worker心跳位于容器 `/tmp/heartbeat`，结果共享卷 `/artifacts`。`docker compose down -v --remove-orphans` 清理本项目测试数据。

本地开发可启动db/redis后，在backend安装 requirements，设置 DATABASE_URL/REDIS_URL/JWT_SECRET，`uvicorn src.main:app --reload`；前端建议仍用Nginx代理，也可设置本地同源代理。`backend/src`按routes/controllers/services/models/schemas/middlewares/config/utils分工；`frontend/src`按api/stores/pages/components/hooks/utils/constants/types/router分工。ORM首次建表，`backend/migrations/001_initial.sql`保留对应DDL；不包含在线版本迁移框架。

环境变量详见 `.env.example`：COMPOSE_PROJECT_NAME、FRONTEND_PORT、BACKEND_PORT、DB_PORT、DB_PASSWORD、JWT_SECRET、SEED_DEMO、NETWORK_SUBNET。显式子网10.253.115.0/24用于规避当前机器默认池耗尽，可迁移时调整。生产使用需替换演示凭据与JWT密钥。

共享枚举：角色ROLES、任务状态STATES、业务组TEAMS、决定DECISIONS；后端 `src/constants/enums.py`、schemas/business.py 与前端 `src/constants/enums.js`，持久化列见models/entities.py。共用表格、表单字段、状态标签组件；表单hooks与HTML转义工具；请求ID、安全响应头两个中间件，业务写入审计。

范围：逐条表单/API录入，无Excel导入、删除、多人并发任务调度或外部话术发布；采纳在站内签核。使用单worker；时间/窗口由业务填入说明，不自动验证客户结构。Google Fonts不可用时回退serif/sans-serif。测试、截图和已知差异在 `../../test-artifacts/gb-3115/TESTING.md`，源码不放证据。许可证 MIT，见 LICENSE。
