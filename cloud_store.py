"""PostgreSQL 영구 저장 및 세션별 메모리 데모. 사용자 파일을 로컬 DB에 저장하지 않습니다."""
from datetime import datetime, timezone
import json
from sqlalchemy import Column, Integer, JSON, MetaData, String, Table, create_engine, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from domain import ValidationError, normalize_item, payload


class ConflictError(ValueError):
    pass


class Repository:
    def __init__(self, url='sqlite+pysqlite:///:memory:'):
        kwargs = {'pool_pre_ping': True, 'json_serializer': lambda v: json.dumps(v, ensure_ascii=False)}
        if url.startswith(('postgres://', 'postgresql://')):
            url = 'postgresql+psycopg://' + url.split('://', 1)[1]
        if url.startswith('postgresql+'):
            kwargs['connect_args'] = {'sslmode': 'require'}
        elif url == 'sqlite+pysqlite:///:memory:':
            kwargs.update(poolclass=StaticPool, connect_args={'check_same_thread': False})
        else:
            raise ValueError('PostgreSQL 또는 세션 메모리 데모만 지원합니다.')
        self.engine = create_engine(url, **kwargs)
        meta = MetaData()
        self.items = Table('cloud_pending_items', meta, Column('id', String(80), primary_key=True), Column('version', Integer, nullable=False), Column('payload', JSON, nullable=False))
        self.events = Table('cloud_pending_events', meta, Column('seq', Integer, primary_key=True, autoincrement=True), Column('item_id', String(80), nullable=False), Column('actor', String(254), nullable=False), Column('action', String(24), nullable=False), Column('created_at', String(40), nullable=False), Column('before_value', JSON), Column('after_value', JSON))
        meta.create_all(self.engine)

    def list_items(self):
        with self.engine.connect() as conn:
            return [{**r.payload, '버전': r.version} for r in conn.execute(select(self.items).order_by(self.items.c.id))]

    def list_events(self, limit=500):
        with self.engine.connect() as conn:
            return [dict(r._mapping) for r in conn.execute(select(self.events).order_by(self.events.c.seq.desc()).limit(limit))]

    def save_item(self, values, actor, expected_version=0):
        row = normalize_item(values)
        return self.apply_plan({'changes': [{'id': row['ID'], 'after': payload(row), 'expected_version': expected_version}], 'conflicts': []}, actor)

    def apply_plan(self, plan, actor):
        if not str(actor).strip() or len(actor) > 254:
            raise ValidationError('변경자 정보가 없습니다.')
        if plan.get('conflicts'):
            raise ConflictError('충돌이 있어 반영할 수 없습니다. 최신 데이터를 다시 비교해주세요.')
        changed = 0
        try:
            with self.engine.begin() as conn:
                for change in plan['changes']:
                    after = payload(normalize_item(change['after']))
                    identifier = change['id']; expected = change['expected_version']
                    if after['ID'] != identifier or not isinstance(expected, int) or isinstance(expected, bool) or expected < 0:
                        raise ValidationError('변경 계획의 ID 또는 버전이 잘못됐습니다.')
                    old = conn.execute(select(self.items).where(self.items.c.id == identifier)).first()
                    if expected == 0:
                        if old:
                            raise ConflictError('이미 등록된 ID입니다. 다시 비교해주세요.')
                        conn.execute(insert(self.items).values(id=identifier, version=1, payload=after))
                        before = None; version = 1
                    else:
                        if old is None or old.version != expected:
                            raise ConflictError('다른 사용자가 수정했습니다. 새로고침 후 다시 비교해주세요.')
                        if old.payload == after:
                            continue
                        before = {**old.payload, '버전': old.version}; version = expected + 1
                        result = conn.execute(update(self.items).where(self.items.c.id == identifier, self.items.c.version == expected).values(version=version, payload=after))
                        if result.rowcount != 1:
                            raise ConflictError('다른 사용자가 수정했습니다. 다시 비교해주세요.')
                    conn.execute(insert(self.events).values(item_id=identifier, actor=actor, action='CREATE' if before is None else 'UPDATE', created_at=datetime.now(timezone.utc).isoformat(), before_value=before, after_value={**after, '버전': version}))
                    changed += 1
        except IntegrityError as exc:
            raise ConflictError('동시에 같은 ID가 등록됐습니다. 최신 데이터를 다시 비교해주세요.') from exc
        return changed
