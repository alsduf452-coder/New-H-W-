"""Single coalesced manual-sync request, separate from measurement data."""
import time
import uuid
from sqlalchemy import MetaData, Table, Column, String, Integer, JSON, select, insert, update
from sqlalchemy.exc import IntegrityError


class SyncControl:
    def __init__(self, engine, initialize=False):
        self.engine=engine
        meta=MetaData()
        self.table=Table('cloud_sync_requests',meta,Column('id',String(40),primary_key=True),Column('version',Integer,nullable=False),Column('payload',JSON,nullable=False))
        if initialize:
            meta.create_all(engine)
            try:
                with engine.begin() as conn:conn.execute(insert(self.table).values(id='manual',version=0,payload={}))
            except IntegrityError:pass

    def _read(self):
        with self.engine.connect() as conn:
            row=conn.execute(select(self.table).where(self.table.c.id=='manual')).mappings().first()
            if row is None:raise RuntimeError('Manual sync not initialized')
            return row['version'],dict(row['payload'])

    def _save(self,version,payload):
        with self.engine.begin() as conn:
            return conn.execute(update(self.table).where(self.table.c.id=='manual',self.table.c.version==version).values(version=version+1,payload=payload)).rowcount==1

    def status(self,now=None):
        now=time.time() if now is None else now
        _,p=self._read()
        if p.get('status') in ('pending','running') and p['expires_at']<=now:
            p.update(status='expired',summary='PC 응답 대기 시간이 지났습니다. 로그인·네트워크·부재 설정을 확인해주세요.')
        return p

    def request(self,actor,now=None):
        now=time.time() if now is None else now
        for _ in range(5):
            version,p=self._read()
            if p.get('status') in ('pending','running') and p['expires_at']>now:return p
            new={'request_id':uuid.uuid4().hex,'status':'pending','actor':str(actor)[:64],'requested_at':now,'expires_at':now+300,'summary':''}
            if self._save(version,new):return new
        raise RuntimeError('Concurrent request; refresh status')

    def claim(self,now=None):
        now=time.time() if now is None else now
        version,p=self._read()
        if p.get('status')!='pending' or p['expires_at']<=now:return None
        p.update(status='running',started_at=now,expires_at=now+1200)
        return p if self._save(version,p) else None

    def finish(self,request_id,status,summary,now=None):
        version,p=self._read()
        if p.get('request_id')!=request_id or p.get('status')!='running':return False
        p.update(status=status,summary=summary[:500],finished_at=time.time() if now is None else now)
        return self._save(version,p)
