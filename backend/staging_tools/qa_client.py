"""Bounded HTTPS workflow QA. Requests are paced, never automatically retried."""
from concurrent.futures import ThreadPoolExecutor
from http.cookies import SimpleCookie
import http.client
import json
import secrets
import socket
import ssl
import time
from urllib.parse import urlencode
from .fixtures import image,scanned_pdf,verify_partial


class Transport:
    def __init__(self,host,port,ca,*,paced=True):
        self.host,self.port=host,port;self.context=ssl.create_default_context(cafile=str(ca))
        self.paced=paced;self.last={'auth':0.,'ocr':0.,'api':0.}
    def pace(self,path):
        group='ocr' if path=='/api/documents/analyze' else 'auth' if path.startswith('/api/auth/') else 'api'
        delay={'ocr':5.1,'auth':12.1,'api':1.05}[group]
        if self.paced:time.sleep(max(0,self.last[group]+delay-time.monotonic()))
        self.last[group]=time.monotonic()
    def request(self,method,path,body=None,*,token=None,content_type='application/json',hostname='api.staging.test',headers=None,pace=True):
        if pace:self.pace(path)
        context=self.context;host=self.host;port=self.port
        class LocalTLS(http.client.HTTPSConnection):
            def connect(self):
                self.sock=context.wrap_socket(socket.create_connection((host,port),timeout=self.timeout),server_hostname=hostname)
        connection=LocalTLS(hostname,timeout=130)
        request_headers={'Host':hostname,'Origin':f'https://app.staging.test:{port}','Content-Type':content_type}
        if token:request_headers['Authorization']='Token '+token
        request_headers.update(headers or {})
        if isinstance(body,(dict,list)):body=json.dumps(body).encode()
        start=time.monotonic()
        try:
            connection.request(method,path,body,request_headers);response=connection.getresponse();raw=response.read()
            output=json.loads(raw) if raw and 'application/json' in response.getheader('Content-Type','') else raw.decode('utf-8',errors='replace')
            return response.status,output,response.getheaders(),round(time.monotonic()-start,4)
        finally:connection.close()
    def upload(self,data,name,token,*,pace=True):
        boundary='----qa-'+secrets.token_hex(12)
        body=f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+data+f'\r\n--{boundary}--\r\n'.encode()
        return self.request('POST','/api/documents/analyze',body,token=token,content_type=f'multipart/form-data; boundary={boundary}',pace=pace)


def run(transport,accounts,expire_callback,*,native=True,font=None):
    rows=[]
    def check(name,response,status):
        actual=response[0]
        if actual!=status:raise AssertionError(f'{name}: expected {status}, received {actual}.')
        rows.append({'case':name,'status':actual,'passed':True,'seconds':response[3]})
        return response[1]
    check('registration_closed',transport.request('POST','/api/auth/register',{'username':'not-created','password':'not-used'}),403)
    login=[]
    for index,account in enumerate(accounts):
        payload=check(f'login_{index+1}',transport.request('POST','/api/auth/login',account),200)
        login.append(payload['token'])
    allowed,denied=login
    check('invalid_credentials',transport.request('POST','/api/auth/login',{'username':accounts[0]['username'],'password':'wrong-synthetic-password'}),401)
    check('unauthorized_checklist',transport.request('GET','/api/checklist'),401)
    check('liveness',transport.request('GET','/api/health'),200)
    ready=transport.request('GET','/api/ready');check('readiness',ready,200)
    security={key.lower():value for key,value in ready[2]}
    assert security['access-control-allow-origin']==f'https://app.staging.test:{transport.port}'
    assert security['x-content-type-options']=='nosniff' and security['referrer-policy']=='no-referrer'
    assert 'frame-ancestors' in security['content-security-policy'] and 'max-age=3600' in security['strict-transport-security']
    preflight=transport.request('OPTIONS','/api/documents/analyze',headers={'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'})
    check('cors_preflight',preflight,204)
    cors={key.lower():value.lower() for key,value in preflight[2]}
    assert 'authorization' in cors['access-control-allow-headers'] and 'post' in cors['access-control-allow-methods']
    rejected=transport.request('GET','/api/ready',headers={'Origin':'https://untrusted.invalid'})
    check('untrusted_cors_origin',rejected,200)
    assert not any(key.lower()=='access-control-allow-origin' for key,value in rejected[2])
    check('life_guides',transport.request('GET','/api/guides'),200)
    check('official_resources',transport.request('GET','/api/resources'),200)
    html=check('frontend_document_decoder',transport.request('GET','/document-decoder',hostname='app.staging.test'),200)
    assert '<div id="root"></div>' in html and 'type="module"' in html
    # Test cookie attributes and CSRF on the actual same-origin admin/session flow.
    cookie_response=transport.request('GET','/admin/login/')
    check('admin_csrf_cookie',cookie_response,200)
    cookies=SimpleCookie()
    for key,value in cookie_response[2]:
        if key.lower()=='set-cookie':cookies.load(value)
    csrf=cookies['csrftoken'];assert csrf['secure'] and csrf['httponly'] and csrf['samesite']=='Strict'
    check('missing_csrf_denied',transport.request('POST','/admin/login/',urlencode(accounts[0]),content_type='application/x-www-form-urlencoded'),403)
    logged=transport.request('POST','/admin/login/',urlencode({**accounts[0],'csrfmiddlewaretoken':csrf.value,'next':'/admin/'}),content_type='application/x-www-form-urlencoded',headers={'Cookie':'csrftoken='+csrf.value,'Origin':f'https://api.staging.test:{transport.port}'})
    check('valid_admin_session',logged,302)
    session=SimpleCookie()
    for key,value in logged[2]:
        if key.lower()=='set-cookie':session.load(value)
    assert session['sessionid']['secure'] and session['sessionid']['httponly'] and session['sessionid']['samesite']=='Strict'
    cookie_header='; '.join(f'{key}={value.value}' for key,value in session.items())
    check('session_api_csrf_denied',transport.request('POST','/api/checklist',{'title':'not-created'},headers={'Cookie':cookie_header}),403)
    created=check('checklist_create',transport.request('POST','/api/checklist',{'title':'Synthetic staging task','category':'QA','dueDate':'2031-06-30','user':999999},token=allowed),201)
    identifier=created['id'];assert created['category']=='QA'
    listed=check('checklist_read',transport.request('GET','/api/checklist',token=allowed),200);assert any(item['id']==identifier for item in listed)
    others=check('checklist_other_account',transport.request('GET','/api/checklist',token=denied),200);assert not any(item['id']==identifier for item in others)
    check('checklist_cross_account_write_denied',transport.request('PATCH',f'/api/checklist/{identifier}',{'completed':True},token=denied),404)
    changed=check('checklist_update',transport.request('PATCH',f'/api/checklist/{identifier}',{'completed':True,'category':'Changed'},token=allowed),200);assert changed['completed'] and changed['category']=='Changed'
    check('checklist_delete',transport.request('DELETE',f'/api/checklist/{identifier}',token=allowed),204)
    check('checklist_recovery_seed',transport.request('POST','/api/checklist',{'title':'Synthetic recovery sentinel','category':'Recovery'},token=allowed),201)
    partial=image('partial',font);unknown=image('unknown',font)
    check('unauthorized_ocr',transport.upload(partial,'synthetic.png',None),401)
    check('unprivileged_ocr',transport.upload(partial,'synthetic.png',denied),403)
    check('invalid_contents',transport.upload(b'not-an-image','synthetic.png',allowed),400)
    first_authorized=time.monotonic()
    if native:
        analyzed=check('partial_document',transport.upload(partial,'synthetic.png',allowed),200);verify_partial(analyzed)
        unknown_result=check('unknown_document',transport.upload(unknown,'unknown.png',allowed),200)
        assert unknown_result['documentType'] is None and unknown_result['primaryDeadline'] is None and unknown_result['primaryAmount'] is None
        scanned=check('two_page_scanned_pdf',transport.upload(scanned_pdf(partial),'synthetic.pdf',allowed),200)
        verify_partial(scanned);assert len(scanned['pages'])==2
    check('corrupted_image',transport.upload(b'\x89PNG\r\n\x1a\ncorrupt','synthetic.png',allowed),400)
    check('corrupted_pdf',transport.upload(b'%PDF-1.7 corrupt','synthetic.pdf',allowed),400)
    # At most six authenticated OCR attempts above. Wait for that user's fixed
    # window to expire; do not weaken limits or retry an earlier request.
    time.sleep(max(0,first_authorized+61-time.monotonic()))
    if native:
        transport.pace('/api/documents/analyze')
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(transport.upload,partial,'synthetic.png',allowed,pace=False) for _ in range(2)]
            concurrent=[f.result(timeout=130) for f in futures]
        assert sorted(response[0] for response in concurrent)==[200,503]
        verify_partial(next(response[1] for response in concurrent if response[0]==200))
        rows.append({'case':'concurrent_ocr','statuses':[r[0] for r in concurrent],'passed':True})
    # Probe the actual configured proxy rate with no authorized heavy work.
    time.sleep(max(0,transport.last['ocr']+10.2-time.monotonic()))
    transport.pace('/api/documents/analyze')
    rapid=[transport.upload(b'x','synthetic.png',None,pace=False)[0] for _ in range(3)]
    assert rapid==[401,401,429]
    rows.append({'case':'proxy_rate_limit','statuses':rapid,'passed':True})
    check('logout',transport.request('POST','/api/auth/logout',{},token=denied),200)
    check('revoked_token',transport.request('GET','/api/auth/me',token=denied),401)
    expire_callback(accounts[0]['username'])
    check('expired_token',transport.request('GET','/api/auth/me',token=allowed),401)
    return {'cases':rows,'passed':all(row['passed'] for row in rows),'nativeCasesExecuted':native,'automaticOcrRetries':0,'sensitiveResultsPersisted':False,'registrationPolicy':'closed_in_production'}
