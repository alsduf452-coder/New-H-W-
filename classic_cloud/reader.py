"""Only SELECT existing sync snapshots. Never initialize or migrate the shared DB."""
from sqlalchemy import create_engine, text


class SnapshotReader:
    def __init__(self, url):
        if url.startswith(('postgres://', 'postgresql://')):
            url = 'postgresql+psycopg://' + url.split('://',1)[1]
        if not url.startswith('postgresql+psycopg://'):
            raise ValueError('운영 PostgreSQL 연결이 필요합니다.')
        self.engine = create_engine(url, pool_pre_ping=True, connect_args={'sslmode':'require','connect_timeout':10})

    def read(self, source_id):
        with self.engine.begin() as connection:
            connection.execute(text('SET TRANSACTION READ ONLY'))
            row = connection.execute(text('SELECT revision, state, previews FROM cloud_local_excel WHERE id = :source'), {'source':source_id}).mappings().first()
            return dict(row) if row else {'revision':0,'state':{},'previews':{}}
