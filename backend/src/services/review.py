"""缺测复核：冻结名单与已知分，按缺项可达取值计算全员平均改善区间。

口径：
- 顾问名单与创建复核时已知的前/后测分数冻结，不随后续样本修订改变。
- 仍缺前测的顾问，差值可能取 [后测-100, 后测]；仍缺后测的，可能取 [-前测, 100-前测]；
  两侧都缺的，差值可能取 [-100, 100]。
- 全员平均改善 = 各顾问差值之和 / 名单人数，上下界由每个缺项取最不利/最有利值得到。
- 下界 >= 改善线即可判定达到；上界 < 改善线即可判定未达到；否则无法判定。
"""
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified

from src.models.entities import Review, ReviewTask, PairCorrection, Pair

MIN_SCORE = 0.0
MAX_SCORE = 100.0
EPS = 1e-9


def now():
    return datetime.now(timezone.utc).isoformat()


def _save_result(review, data):
    """JSON 列不会被原地修改跟踪，统一赋新字典并标脏。"""
    review.result = data
    flag_modified(review, "result")


def _latest_corrections(s, review_id):
    """同一复核内每个缺项以最后一条回填为准。"""
    latest = {}
    rows = (
        s.query(PairCorrection)
        .filter_by(review_id=review_id)
        .order_by(PairCorrection.id)
        .all()
    )
    for row in rows:
        latest[(row.code, row.field)] = row.new_value
    return latest


def _entry(row, corrections):
    code = row["code"]
    frozen_before = row.get("before")
    frozen_after = row.get("after")
    before = frozen_before if frozen_before is not None else corrections.get((code, "before"))
    after = frozen_after if frozen_after is not None else corrections.get((code, "after"))
    before_missing = before is None
    after_missing = after is None
    if before_missing and after_missing:
        low, high = -MAX_SCORE, MAX_SCORE
    elif before_missing:
        low, high = after - MAX_SCORE, after - MIN_SCORE
    elif after_missing:
        low, high = MIN_SCORE - before, MAX_SCORE - before
    else:
        low = high = after - before
    return {
        "code": code,
        "team": row.get("team"),
        "before": before,
        "after": after,
        "before_frozen": frozen_before is not None,
        "after_frozen": frozen_after is not None,
        "before_missing": before_missing,
        "after_missing": after_missing,
        "difference": None if (before_missing or after_missing) else after - before,
        "lower": low,
        "upper": high,
    }


def _task_dict(task):
    return {
        "id": task.id,
        "code": task.code,
        "team": task.team,
        "missing": task.missing,
        "state": task.state,
        "attempts": task.attempts,
        "created": task.created,
        "updated": task.updated,
        "note": task.note,
    }


def _decision(lower, upper, threshold):
    if lower >= threshold - EPS:
        return "pass"
    if upper < threshold - EPS:
        return "fail"
    return "undetermined"


def _compute(s, review):
    roster = (review.result or {}).get("roster") or []
    if not roster:
        raise HTTPException(422, "复核缺少冻结顾问名单")
    corrections = _latest_corrections(s, review.id)
    entries = [_entry(row, corrections) for row in roster]
    n = len(entries)
    lower = sum(item["lower"] for item in entries) / n
    upper = sum(item["upper"] for item in entries) / n
    threshold = float(review.threshold)
    verdict = _decision(lower, upper, threshold)

    tasks = (
        s.query(ReviewTask)
        .filter_by(review_id=review.id)
        .order_by(ReviewTask.id)
        .all()
    )
    used = len(tasks)
    slots = int(review.slots or 0)
    remaining = max(slots - used, 0)
    outstanding = sum(1 for task in tasks if task.state == "dispatched")
    known_entries = [item for item in entries if item["difference"] is not None]
    missing_fields = [
        {"code": item["code"], "field": field}
        for item in entries
        for field in ("before", "after")
        if item[field + "_missing"]
    ]
    existing = {(task.code, task.missing) for task in tasks}
    dispatchable = [
        item for item in missing_fields if (item["code"], item["field"]) not in existing
    ]
    closing = (review.result or {}).get("closing")
    data = {
        "roster": roster,
        "created_at": (review.result or {}).get("created_at"),
        "created_by": (review.result or {}).get("created_by"),
        "late_returns": (review.result or {}).get("late_returns", []),
        "threshold": threshold,
        "lower": lower,
        "upper": upper,
        "reachable": {"min": lower, "max": upper},
        "verdict": verdict,
        "n_total": n,
        "n_known": len(known_entries),
        "n_missing_advisors": sum(
            1 for item in entries if item["before_missing"] or item["after_missing"]
        ),
        "missing_fields": missing_fields,
        "dispatchable": dispatchable,
        "known_difference_sum": sum(item["difference"] for item in known_entries),
        "slots": slots,
        "slots_used": used,
        "slots_remaining": remaining,
        "outstanding": outstanding,
        "entries": entries,
        "tasks": [_task_dict(task) for task in tasks],
        "closing": closing,
        "roster_frozen": True,
        "warning": (
            "区间按缺项可取 0–100 的最不利/最有利组合计算，覆盖整份冻结名单；"
            "它只回答“平均改善是否可能达到改善线”，不替代完整配对后的统计检验。"
        ),
    }
    return data


def _close(review, data, state):
    review.state = state
    review.verdict = data["verdict"]
    if not data.get("closing"):
        data["closing"] = {
            "closed_at": now(),
            "state": state,
            "verdict": data["verdict"],
            "threshold": data["threshold"],
            "lower": data["lower"],
            "upper": data["upper"],
            "n_total": data["n_total"],
            "n_known": data["n_known"],
            "known_difference_sum": data["known_difference_sum"],
            "tasks_outstanding": [
                {"code": task["code"], "missing": task["missing"]}
                for task in data.get("tasks", [])
                if task["state"] == "dispatched"
            ],
            "scores": [
                {
                    "code": item["code"],
                    "team": item["team"],
                    "before": item["before"],
                    "after": item["after"],
                    "difference": item["difference"],
                    "lower": item["lower"],
                    "upper": item["upper"],
                }
                for item in data["entries"]
            ],
            "basis": "冻结名单已知分 + 结案前已收缺项回填",
        }
    if state == "undetermined":
        if data.get("slots_remaining", 0) <= 0:
            data["reason"] = "可设名额已用完且回分到齐，区间仍无法判定"
        else:
            data["reason"] = "全部缺项均已派单并回分，区间仍无法判定"
    else:
        data["reason"] = "可达区间已能判定，停止派单并结案"


def _settle(review, data):
    """根据区间与名额状态推进复核；已能定论即结案，否则保持开放。

    无法定论的终止条件：名额用完，或所有缺项都已派过单且已全部回分——
    两种情况下再派单也不会产生新信息。
    """
    no_new_leads = not data.get("dispatchable")
    if data["verdict"] != "undetermined":
        _close(review, data, "concluded")
    elif data["slots_remaining"] <= 0 and data["outstanding"] == 0:
        _close(review, data, "undetermined")
    elif no_new_leads and data["outstanding"] == 0:
        _close(review, data, "undetermined")
    else:
        review.state = "open"
        review.verdict = None
    _save_result(review, data)
    return data


def recompute(s, review):
    """从冻结名单与已收回到分重算区间；结案/无法定论后不再改动结案依据。"""
    if review.state != "open":
        return review.result or {}
    data = _compute(s, review)
    _settle(review, data)
    s.commit()
    return review.result


def create(s, evaluation, threshold, slots, actor):
    snapshot = (evaluation.result or {}).get("snapshot")
    if not isinstance(snapshot, list) or not snapshot:
        raise HTTPException(422, "该评估没有可用的冻结样本，无法建立缺测复核")
    roster = []
    seen = set()
    for row in snapshot:
        code = str(row.get("code"))
        if code in seen:
            continue
        seen.add(code)
        roster.append(
            {
                "code": code,
                "team": row.get("team"),
                "before": row.get("before"),
                "after": row.get("after"),
            }
        )
    if not roster:
        raise HTTPException(422, "冻结样本中没有顾问记录")
    review = Review(
        evaluation_id=evaluation.id,
        threshold=threshold,
        slots=slots,
        state="open",
        error="",
        result={"roster": roster, "created_at": now(), "created_by": actor.email},
    )
    s.add(review)
    s.commit()
    recompute(s, review)
    return review


def lock(s, review_id):
    query = s.query(Review).filter_by(id=review_id)
    if s.get_bind().dialect.name == "postgresql":
        query = query.with_for_update()
    review = query.one_or_none()
    if not review:
        raise HTTPException(404, "缺测复核不存在")
    return review


def dispatch(s, review, count, actor, request_key=None):
    """按名额逐项派补查。行锁 + 唯一键保证并发不超额、重试不重复占名额。"""
    if request_key:
        replay = (
            s.query(ReviewTask)
            .filter_by(review_id=review.id, request_key=request_key)
            .order_by(ReviewTask.id)
            .all()
        )
        if replay:
            # 同一请求键重放：直接返回既有派单，不再占用名额（结案后重试也保持幂等）。
            data = dict(review.result or {})
            data["dispatched_now"] = [task.id for task in replay]
            data["replayed"] = True
            _save_result(review, data)
            s.commit()
            return review.result
    if review.state != "open":
        raise HTTPException(409, "复核已结案或已无法定论，停止派单")
    data = _compute(s, review)
    if data["verdict"] != "undetermined":
        _settle(review, data)
        s.commit()
        raise HTTPException(409, "可达区间已能定论，停止派单并结案")
    if data["slots_remaining"] <= 0:
        _settle(review, data)
        s.commit()
        raise HTTPException(409, "可设补查名额已用完，不能继续派单")

    existing = {(task.code, task.missing) for task in s.query(ReviewTask).filter_by(review_id=review.id).all()}
    candidates = [
        item
        for item in data["missing_fields"]
        if (item["code"], item["field"]) not in existing
    ]
    candidates.sort(key=lambda item: (item["code"], item["field"]))
    if not candidates:
        _settle(review, data)
        s.commit()
        return review.result
    limit = data["slots_remaining"] if count is None else min(count, data["slots_remaining"])
    chosen = candidates[:limit]
    used = data["slots_used"]
    created = []
    for offset, item in enumerate(chosen):
        team = next(
            entry["team"] for entry in data["entries"] if entry["code"] == item["code"]
        )
        task = ReviewTask(
            review_id=review.id,
            code=item["code"],
            team=team,
            missing=item["field"],
            state="dispatched",
            dispatch_key=item["code"] + ":" + item["field"],
            request_key=request_key,
            slot_no=used + offset + 1,
            attempts=1,
            created=now(),
            updated=now(),
            note="",
        )
        s.add(task)
        created.append(task)
    try:
        s.commit()
    except IntegrityError:
        # 唯一键兜底：另一个并发请求已经派了同一顾问同一缺项，不重复占名额。
        s.rollback()
        data = _compute(s, review)
        _settle(review, data)
        s.commit()
        raise HTTPException(409, "并发派单冲突，已按已派记录刷新；请重试确认剩余名额")

    data = _compute(s, review)
    _settle(review, data)
    review.result["dispatched_now"] = [task.id for task in created]
    _save_result(review, review.result)
    s.commit()
    return review.result


def retry(s, review, task_id, actor):
    """补查重试：只累加尝试次数，沿用原派单键，不新增名额占用。"""
    if review.state != "open":
        raise HTTPException(409, "复核已结案或已无法定论，无需重试派单")
    task = s.query(ReviewTask).filter_by(id=task_id, review_id=review.id).one_or_none()
    if not task:
        raise HTTPException(404, "补查派单不存在")
    if task.state == "returned":
        raise HTTPException(409, "该补查已回分，无需重试")
    task.attempts = (task.attempts or 1) + 1
    task.updated = now()
    s.commit()
    data = _compute(s, review)
    _settle(review, data)
    s.commit()
    return review.result


def _roster_entry(review, code):
    roster = (review.result or {}).get("roster") or []
    for row in roster:
        if row["code"] == code:
            return row
    return None


def _mark_returned(s, review, code, fields):
    changed = False
    tasks = s.query(ReviewTask).filter_by(review_id=review.id, code=code).all()
    for task in tasks:
        if task.state == "dispatched" and task.missing in fields:
            task.state = "returned"
            task.updated = now()
            changed = True
    return changed


def _refresh_task_view(review, s):
    tasks = (
        s.query(ReviewTask)
        .filter_by(review_id=review.id)
        .order_by(ReviewTask.id)
        .all()
    )
    if review.result is None:
        return
    data = dict(review.result)
    data["tasks"] = [_task_dict(task) for task in tasks]
    data["slots_used"] = len(tasks)
    data["slots_remaining"] = max(int(review.slots or 0) - len(tasks), 0)
    data["outstanding"] = sum(1 for task in tasks if task.state == "dispatched")
    _save_result(review, data)


def record_return(s, review, actor, code, before=None, after=None, task_id=None, source=""):
    """回填缺项并重算区间。结案后到达的晚到记录照收，但不改结案依据。"""
    row = _roster_entry(review, code)
    if not row:
        raise HTTPException(422, "该顾问不在本次复核的冻结名单中")

    task = None
    if task_id is not None:
        task = s.query(ReviewTask).filter_by(id=task_id, review_id=review.id).one_or_none()
        if not task:
            raise HTTPException(404, "补查派单不存在")
        if task.code != code:
            raise HTTPException(422, "回分顾问与补查派单不一致")

    provided = {}
    if before is not None:
        provided["before"] = before
    if after is not None:
        provided["after"] = after
    if not provided:
        raise HTTPException(422, "请至少填写一个缺项分数")

    for field in provided:
        if row.get(field) is not None:
            raise HTTPException(409, "该分数在复核创建时已冻结，不能通过补查回填改写")
    if task and task.missing not in provided:
        raise HTTPException(422, "本次回分未包含补查派单要求的缺项")

    pair = s.query(Pair).filter_by(code=code).first()
    if not pair:
        raise HTTPException(422, "配对样本记录不存在")
    corrections = _latest_corrections(s, review.id)
    late = review.state != "open"
    added = 0
    for field, value in provided.items():
        if corrections.get((code, field)) == value:
            continue
        s.add(
            PairCorrection(
                review_id=review.id,
                pair_id=pair.id,
                code=code,
                field=field,
                old_value=corrections.get((code, field)),
                new_value=value,
                source=source or "补查回分",
                actor=actor.email,
                created=now(),
                late=late,
            )
        )
        added += 1
    for field, value in provided.items():
        if getattr(pair, field) is None:
            setattr(pair, field, value)
        # 配对样本已有值时只记回填与复核证据，不覆盖样本录入结果。
    _mark_returned(s, review, code, set(provided))

    if review.state == "open":
        s.commit()
        return recompute(s, review)
    # 已结案：收下晚到记录，不改 closing，也不改写结案时的区间；只刷新任务视图并留痕。
    data = dict(review.result or {})
    if added:
        data.setdefault("late_returns", []).append(
            {
                "code": code,
                "fields": provided,
                "source": source or "补查回分",
                "actor": actor.email,
                "created": now(),
            }
        )
    _save_result(review, data)
    _refresh_task_view(review, s)
    s.commit()
    return review.result


def recover_open(s):
    """回分/结案中断后恢复：未结案的复核按已收回到分重算，已结案的不动结案依据。"""
    recovered = []
    for review in s.query(Review).filter_by(state="open").all():
        try:
            recompute(s, review)
            recovered.append(review.id)
        except Exception:
            s.rollback()
    return recovered


def sync_pair_backfill(s, pair, actor):
    """样本修订回填缺项时，自动同步到所有包含该顾问的复核。

    已知分冻结，不因修订而改写；只有创建复核时缺失、现在补上的分数才进入区间。
    结案后补上的按晚到记录收取，结案依据保持不变。
    """
    reviews = s.query(Review).all()
    touched = False
    for review in reviews:
        row = _roster_entry(review, pair.code)
        if not row:
            continue
        fields = set()
        for field in ("before", "after"):
            if row.get(field) is None and getattr(pair, field) is not None:
                fields.add(field)
        if not fields:
            continue
        if s.get_bind().dialect.name == "postgresql":
            s.query(Review).filter_by(id=review.id).with_for_update().one()
        corrections = _latest_corrections(s, review.id)
        late = review.state != "open"
        added = False
        for field in fields:
            value = getattr(pair, field)
            if corrections.get((pair.code, field)) == value:
                continue
            s.add(
                PairCorrection(
                    review_id=review.id,
                    pair_id=pair.id,
                    code=pair.code,
                    field=field,
                    old_value=corrections.get((pair.code, field)),
                    new_value=value,
                    source="样本修订回填",
                    actor=actor.email,
                    created=now(),
                    late=late,
                )
            )
            added = True
        _mark_returned(s, review, pair.code, fields)
        touched = True
        if review.state == "open":
            s.commit()
            recompute(s, review)
        else:
            data = dict(review.result or {})
            if added:
                data.setdefault("late_returns", []).append(
                    {
                        "code": pair.code,
                        "fields": {field: getattr(pair, field) for field in fields},
                        "source": "样本修订回填",
                        "actor": actor.email,
                        "created": now(),
                    }
                )
            _save_result(review, data)
            _refresh_task_view(review, s)
            s.commit()
    return touched
