"""Authenticated, single-source Excel ingestion service (run separately from Streamlit)."""
import hashlib
import hmac
import json
import os
import re
from fastapi import FastAPI, HTTPException, Request, Depends
from starlette.concurrency import run_in_threadpool
from cloud_store import Repository, ConflictError
from domain import ValidationError, FIELDS
from excel_sync import MAX_FILE
from workbook_mapping import workbook_view


def load_mapping(raw):
    try:
        mapping = json.loads(raw or '{}')
        if not isinstance(mapping, dict):
            raise ValueError()
        if not isinstance(mapping.get('pending_sheet', 'PENDING'), str):
            raise ValueError()
        row = mapping.get('header_row', 1)
        if not isinstance(row, int) or isinstance(row, bool) or not 1 <= row <= 100:
            raise ValueError()
        for key in ('columns', 'status_values', 'category_values'):
            values = mapping.get(key, {})
            if not isinstance(values, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in values.items()):
                raise ValueError()
        if set(mapping.get('columns', {})) - set(FIELDS):
            raise ValueError()
        return mapping
    except (ValueError, TypeError):
        raise ValueError('SYNC_MAPPING_JSON 설정을 확인해주세요.') from None


def create_app(repository=None, token=None, source_id=None, mapping=None):
    token = token if token is not None else os.environ.get('SYNC_TOKEN', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43,}', token):
        raise ValueError('SYNC_TOKEN에는 secrets.token_urlsafe(32)로 만든 전용 토큰이 필요합니다.')
    source_id = source_id or os.environ.get('SYNC_SOURCE_ID', 'local-excel')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', source_id):
        raise ValueError('SYNC_SOURCE_ID는 영문·숫자·밑줄·하이픈 80자 이내로 설정해주세요.')
    mapping = load_mapping(json.dumps(mapping)) if mapping is not None else load_mapping(os.environ.get('SYNC_MAPPING_JSON', '{}'))
    mapping_hash = hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest()
    if repository is None:
        url = os.environ.get('DATABASE_URL', '')
        if not url.startswith(('postgres://', 'postgresql://', 'postgresql+psycopg://')):
            raise ValueError('운영 PostgreSQL DATABASE_URL이 필요합니다.')
        try:
            repository = Repository(url)
        except Exception:
            raise RuntimeError('운영 DB 연결에 실패했습니다. DATABASE_URL과 접근 권한을 확인해주세요.') from None
    app = FastAPI(title='Local Excel Sync', docs_url=None, redoc_url=None, openapi_url=None)

    def authorize(request: Request):
        supplied = request.headers.get('authorization', '')
        if not hmac.compare_digest(supplied.encode(), ('Bearer ' + token).encode()):
            raise HTTPException(401, '동기화 인증에 실패했습니다.')

    @app.get('/healthz')
    def health():
        return {'status': 'ok'}

    @app.get('/v1/source/status', dependencies=[Depends(authorize)])
    def status():
        current = repository.local_status(source_id)
        return {**current, 'source_id': source_id, 'resend_required': current.get('mapping_hash') != mapping_hash or current.get('pending_status') == 'conflict'}

    @app.post('/v1/source/workbook', dependencies=[Depends(authorize)])
    async def upload(request: Request):
        raw_revision = request.headers.get('if-match', '')
        if not re.fullmatch(r'\d{1,12}', raw_revision):
            raise HTTPException(428, '현재 서버 revision을 If-Match로 전달해주세요.')
        size = request.headers.get('content-length')
        if size and (not size.isdecimal() or int(size) > MAX_FILE):
            raise HTTPException(413, 'Excel은 20MB 이하여야 합니다.')
        if request.headers.get('content-type', '').split(';')[0] not in ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/octet-stream'):
            raise HTTPException(415, '.xlsx 파일 본문을 전송해주세요.')
        content = bytearray()
        async for block in request.stream():
            content.extend(block)
            if len(content) > MAX_FILE:
                raise HTTPException(413, 'Excel은 20MB 이하여야 합니다.')
        content = bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        if request.headers.get('x-content-sha256') != digest:
            raise HTTPException(400, '파일 해시가 일치하지 않습니다.')
        try:
            previews, pending, warning = await run_in_threadpool(workbook_view, content, mapping)
        except ValidationError as exc:
            raise HTTPException(422, str(exc)) from None
        except Exception:
            raise HTTPException(422, '정상적인 Excel 파일인지 확인해주세요.') from None
        # Store only the bounded preview and normalized data, not the original file.
        previews = {name: {'rows': [[str(v)[:2000] if v is not None else '' for v in row] for row in sheet['rows']], 'truncated': sheet['truncated']} for name, sheet in previews.items()}
        if len(json.dumps(previews, ensure_ascii=False).encode()) > 8 * 1024 * 1024:
            raise HTTPException(422, '시트 미리보기 데이터가 너무 큽니다. 불필요한 긴 셀 내용을 줄여주세요.')
        state = {'file_hash': digest, 'mapping_hash': mapping_hash, 'warning': warning, 'sheet_names': list(previews)}
        try:
            result = await run_in_threadpool(repository.ingest_local, source_id, int(raw_revision), state, previews, pending)
        except ConflictError as exc:
            raise HTTPException(409, str(exc)) from None
        except ValidationError as exc:
            raise HTTPException(422, str(exc)) from None
        except Exception:
            raise HTTPException(503, 'DB 반영에 실패했습니다. 다음 확인 시 다시 시도해주세요.') from None
        return result

    return app
