"""Optional narrow control API and stateless MCP adapter. Disabled without a separate token."""
import hmac
import json
import re
from fastapi import Request,HTTPException,Depends
from starlette.responses import JSONResponse,Response
from starlette.concurrency import run_in_threadpool

TOOLS=[
 {'name':'request_excel_sync','description':'Queue one Excel sync on the user PC only when the user explicitly requests it. Requires PC login, network and no pause/absence. A pending result is not a completed sync.',
  'inputSchema':{'type':'object','properties':{},'additionalProperties':False},
  'annotations':{'readOnlyHint':False,'destructiveHint':False,'idempotentHint':False,'openWorldHint':True}},
 {'name':'get_excel_sync_status','description':'Read current sync state. Pass the request_id returned by request_excel_sync to avoid confusing it with another request.',
  'inputSchema':{'type':'object','properties':{'request_id':{'type':'string','pattern':'^[a-f0-9]{32}$'}},'additionalProperties':False},
  'annotations':{'readOnlyHint':True,'destructiveHint':False,'idempotentHint':True,'openWorldHint':False}}
]


def mount_control(app,control,token='',upload_token=''):
    if not token:return  # No public unauthenticated fallback.
    if not re.fullmatch(r'[A-Za-z0-9_-]{43,}',token) or hmac.compare_digest(token,upload_token):
        raise ValueError('SYNC_CONTROL_TOKEN must be a separate random token of at least 43 characters.')

    def authorize(request:Request):
        supplied=request.headers.get('authorization','')
        if not hmac.compare_digest(supplied.encode(),('Bearer '+token).encode()):
            raise HTTPException(401,'Control authentication required',headers={'WWW-Authenticate':'Bearer'})

    def public_state(state):
        allowed=('request_id','status','requested_at','started_at','finished_at','expires_at','summary')
        return {k:state[k] for k in allowed if k in state}

    def status(request_id=None):
        current=public_state(control.status())
        if request_id and current.get('request_id')!=request_id:
            return {'request_id':request_id,'status':'superseded','summary':'A different request is current; completion of this request cannot be confirmed.'}
        return current or {'status':'idle'}

    @app.post('/v1/control/sync',dependencies=[Depends(authorize)])
    def request_sync():return public_state(control.request('chat-control'))

    @app.get('/v1/control/sync',dependencies=[Depends(authorize)])
    def get_status(request_id:str|None=None):
        if request_id and not re.fullmatch(r'[a-f0-9]{32}',request_id):raise HTTPException(422,'Invalid request_id')
        return status(request_id)

    @app.post('/mcp',dependencies=[Depends(authorize)])
    async def mcp(request:Request):
        body=bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body)>16384:raise HTTPException(413,'Request too large')
        try:message=json.loads(body)
        except (ValueError,UnicodeDecodeError):return JSONResponse({'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}})
        if not isinstance(message,dict) or message.get('jsonrpc')!='2.0':
            return JSONResponse({'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Invalid request'}})
        identifier=message.get('id');method=message.get('method');params=message.get('params',{})
        def error(code,msg):return JSONResponse({'jsonrpc':'2.0','id':identifier,'error':{'code':code,'message':msg}})
        if 'id' not in message:
            # Notifications never perform writes.
            return Response(status_code=202)
        if not isinstance(params,dict):return error(-32602,'Invalid params')
        if method=='initialize':
            requested=params.get('protocolVersion')
            version=requested if requested in ('2025-03-26','2025-06-18','2025-11-25') else '2025-03-26'
            result={'protocolVersion':version,'capabilities':{'tools':{}},'serverInfo':{'name':'hw-excel-sync-control','version':'1.0.0'}}
        elif method=='ping':result={}
        elif method=='tools/list':result={'tools':TOOLS}
        elif method=='tools/call':
            name=params.get('name');args=params.get('arguments',{})
            if not isinstance(args,dict):return error(-32602,'Invalid arguments')
            if name=='request_excel_sync':
                if args:return error(-32602,'No arguments accepted')
                action=lambda:public_state(control.request('mcp-control'))
            elif name=='get_excel_sync_status':
                if set(args)-{'request_id'} or ('request_id' in args and (not isinstance(args['request_id'],str) or not re.fullmatch(r'[a-f0-9]{32}',args['request_id']))):return error(-32602,'Invalid request_id')
                action=lambda:status(args.get('request_id'))
            else:return error(-32602,'Unknown tool')
            try:
                state=await run_in_threadpool(action)
                result={'content':[{'type':'text','text':json.dumps(state,ensure_ascii=False)}],'isError':False}
            except Exception:
                result={'content':[{'type':'text','text':'Sync control unavailable; no successful completion was confirmed.'}],'isError':True}
        else:return error(-32601,'Method not found')
        return JSONResponse({'jsonrpc':'2.0','id':identifier,'result':result})
