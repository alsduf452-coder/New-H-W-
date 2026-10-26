"""PostgreSQL 영구 저장 및 세션별 메모리 데모. 사용자 파일을 로컬 DB에 저장하지 않습니다."""
from datetime import datetime, timezone
from contextlib import nullcontext
import json
import hashlib
from sqlalchemy import Column, Integer, JSON, MetaData, String, Table, create_engine, insert, select, update, text
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
        self.sources = Table('cloud_excel_sources', meta, Column('id', String(500), primary_key=True), Column('revision', Integer, nullable=False), Column('snapshot', JSON, nullable=False))
        self.uploads = Table('cloud_local_excel', meta, Column('id', String(100), primary_key=True), Column('revision', Integer, nullable=False), Column('state', JSON, nullable=False), Column('previews', JSON, nullable=False))
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

    def apply_plan(self, plan, actor, _connection=None):
        if not str(actor).strip() or len(actor) > 254:
            raise ValidationError('변경자 정보가 없습니다.')
        if plan.get('conflicts'):
            raise ConflictError('충돌이 있어 반영할 수 없습니다. 최신 데이터를 다시 비교해주세요.')
        changed = 0
        try:
            with (self.engine.begin() if _connection is None else nullcontext(_connection)) as conn:
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


    def source_snapshot(self, source_id):
        with self.engine.connect() as conn:
            row = conn.execute(select(self.sources).where(self.sources.c.id == source_id)).first()
            return row.snapshot if row else None

    def sync_source(self, source_id, etag, incoming, actor="local-excel-sync", _connection=None):
        from workbook_mapping import source_plan
        try:
            with (self.engine.begin() if _connection is None else nullcontext(_connection)) as conn:
                source = conn.execute(select(self.sources).where(self.sources.c.id == source_id).with_for_update()).first()
                if source and source.snapshot['etag'] == etag:
                    return {'changed': 0, 'missing': [], 'conflicts': []}
                previous = source.snapshot['rows'] if source else []
                current = [{**r.payload, '버전': r.version} for r in conn.execute(select(self.items))]
                plan = source_plan(current, previous, incoming)
                if plan['conflicts']:
                    return {'changed': 0, **plan}
                snapshot = {'etag': etag, 'rows': incoming, 'synced_at': datetime.now(timezone.utc).isoformat()}
                if source:
                    result = conn.execute(update(self.sources).where(self.sources.c.id == source_id, self.sources.c.revision == source.revision).values(revision=source.revision+1, snapshot=snapshot))
                    if result.rowcount != 1:
                        raise ConflictError('다른 세션이 동기화했습니다. 다음 확인 시 다시 시도합니다.')
                else:
                    conn.execute(insert(self.sources).values(id=source_id, revision=1, snapshot=snapshot))
                count = self.apply_plan(plan, actor, _connection=conn)
                return {'changed': count, 'missing': plan['missing'], 'conflicts': []}
        except IntegrityError:
            raise ConflictError('다른 세션이 동기화했습니다. 다음 확인 시 다시 시도합니다.') from None


    def local_status(self, source_id):
        with self.engine.connect() as conn:
            row = conn.execute(select(self.uploads.c.revision, self.uploads.c.state).where(self.uploads.c.id == source_id)).first()
            return {'revision': row.revision, **row.state} if row else {'revision': 0}

    def local_previews(self, source_id):
        with self.engine.connect() as conn:
            row = conn.execute(select(self.uploads.c.previews).where(self.uploads.c.id == source_id)).first()
            return row.previews if row else {}

    def ingest_local(self, source_id, expected_revision, state, previews, pending):
        """Persist the preview, import baseline, audit and Pending changes together."""
        try:
            with self.engine.begin() as conn:
                if self.engine.dialect.name == 'postgresql':
                    lock = int.from_bytes(hashlib.sha256(source_id.encode()).digest()[:8], 'big', signed=True)
                    conn.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': lock})
                old = conn.execute(select(self.uploads).where(self.uploads.c.id == source_id)).first()
                revision = old.revision if old else 0
                if revision != expected_revision:
                    raise ConflictError('서버 파일 버전이 변경됐습니다. 다시 확인 후 전송해주세요.')
                result = {'changed': 0, 'conflicts': [], 'missing': []}
                if pending is not None:
                    result = self.sync_source('local:' + source_id, state['file_hash'] + ':' + state['mapping_hash'], pending, _connection=conn)
                state = {**state, 'changed': result['changed'], 'conflicts': result['conflicts'], 'missing_count': len(result['missing']), 'pending_status': 'mapping_required' if pending is None else 'conflict' if result['conflicts'] else 'applied', 'received_at': datetime.now(timezone.utc).isoformat()}
                if old:
                    changed = conn.execute(update(self.uploads).where(self.uploads.c.id == source_id, self.uploads.c.revision == revision).values(revision=revision+1, state=state, previews=previews))
                    if changed.rowcount != 1:
                        raise ConflictError('동시 전송이 감지됐습니다. 다시 확인 후 전송해주세요.')
                else:
                    conn.execute(insert(self.uploads).values(id=source_id, revision=1, state=state, previews=previews))
                return {'revision': revision+1, **state}
        except IntegrityError:
            raise ConflictError('동시 전송이 감지됐습니다. 다시 확인 후 전송해주세요.') from None
