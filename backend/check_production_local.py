"""Bounded production-profile HTTP smoke; disposable accounts/DB, no deployment.

Uses existing official Medium models and explicitly synthetic images. Never writes
response evidence, credentials, or raw OCR. Dense images require 5 GiB available
host RAM; the explicitly bounded 480x480 synthetic mode requires 3 GiB.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time

import psutil


def verify_small_fields(result):
    # Independent facts from the explicitly generated fixture above, never used
    # as hints by the endpoint or its analyzer.
    assert result['documentType']=='Residence Tax'
    assert result['primaryDeadline']=='2031-06-30' and result['primaryAmount']==5000
    assert any(d['kind']=='payment' and d['date']=='2031-06-30' and d['status']=='verified' and d['label']=='Payment deadline' for d in result['deadlines'])
    assert any(a['kind']=='payment' and a['value']==5000 and a['status']=='verified' and a['label']=='Payment amount' for a in result['amounts'])


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser()
    inputs=parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--image',type=Path,help='Explicitly synthetic PNG, e.g. evaluation fixture S001.')
    inputs.add_argument('--small-synthetic',action='store_true',help='Render a bounded 480x480 Japanese test image in memory.')
    parser.add_argument('--font',type=Path,help='Installed Japanese-capable font for small-synthetic mode on other platforms.')
    parser.add_argument('--output',type=Path,required=True,help='Private aggregate metrics JSON outside source checkout.')
    args=parser.parse_args()
    project=Path(__file__).resolve().parents[1]
    image=args.image.expanduser().resolve() if args.image else None
    output=args.output.expanduser().resolve()
    if output.is_relative_to(project):raise ValueError('Keep smoke artifacts outside the checkout.')
    minimum_available=(3 if args.small_synthetic else 5)*1024**3
    if psutil.virtual_memory().available<minimum_available:raise RuntimeError('Insufficient available host memory for this native smoke workload.')
    if args.small_synthetic:
        from io import BytesIO
        from PIL import Image,ImageDraw,ImageFont
        font=ImageFont.truetype(str(args.font or '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'),27)
        buffer=BytesIO()
        with Image.new('RGB',(480,480),'white') as generated:
            draw=ImageDraw.Draw(generated)
            for row,line in enumerate(['住民税 納付書','納期限 2031年6月30日','納付額 5,000円']):
                draw.text((24,40+row*110),line,font=font,fill='black')
            generated.save(buffer,format='PNG')
        data=buffer.getvalue()
    else:data=image.read_bytes()
    original_hash=hashlib.sha256(data).digest()
    if len(data)>10*1024**2 or (image and image.suffix.lower()!='.png'):raise ValueError('Use one bounded generated PNG.')
    dev_database=project/'backend/db.sqlite3'
    original_db=dev_database.read_bytes() if dev_database.exists() else None
    model_root=Path(os.environ.get('DOCUMENT_OCR_MODEL_ROOT') or Path.home()/'.paddlex/official_models').expanduser().resolve()
    with tempfile.TemporaryDirectory(prefix='jxtw-production-smoke-') as directory:
        root=Path(directory);state=root/'state';state.mkdir(mode=0o700);(state/'tmp').mkdir(mode=0o700)
        os.environ.update(DJANGO_SETTINGS_MODULE='config.settings_production',DJANGO_SECRET_KEY=secrets.token_urlsafe(64),
            DJANGO_ALLOWED_HOSTS='api.example.test',DJANGO_CORS_ALLOWED_ORIGINS='https://app.example.test',
            DJANGO_CSRF_TRUSTED_ORIGINS='https://app.example.test,https://api.example.test',DJANGO_TRUSTED_PROXY_IPS='127.0.0.1',
            DJANGO_STATE_DIR=str(state),DJANGO_STATIC_ROOT=str(root/'static'),DOCUMENT_OCR_MODEL_ROOT=str(model_root))
        import django;django.setup()
        from django.core.management import call_command
        from django.contrib.auth.models import User,Permission
        from django.db import connections
        from io import StringIO
        check_output=StringIO()
        call_command('check',deploy=True,stdout=check_output,stderr=check_output)
        deployment_warnings=[code for code in ('security.W005','security.W021') if code in check_output.getvalue()]
        call_command('migrate',interactive=False,stdout=StringIO())
        call_command('migrate',interactive=False,stdout=StringIO())
        password=secrets.token_urlsafe(32)
        user=User.objects.create_user('synthetic-integration-user',password=password)
        user.user_permissions.add(Permission.objects.get(codename='analyze_document'))
        connections.close_all()
        with socket.socket() as available:
            available.bind(('127.0.0.1',0));port=available.getsockname()[1]
        env={**os.environ,'JXTW_BIND':f'127.0.0.1:{port}'}
        log=root/'operations.log'
        boundary='----jxtw-'+secrets.token_hex(16)
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="synthetic.png"\r\nContent-Type: image/png\r\n\r\n'.encode()+data+f'\r\n--{boundary}--\r\n'.encode())
        token=None
        def request(method,path,payload=None,authenticated=True,content_type='application/json'):
            headers={'Host':'api.example.test','X-Forwarded-Proto':'https','Content-Type':content_type}
            if authenticated and token:headers['Authorization']='Token '+token
            connection=http.client.HTTPConnection('127.0.0.1',port,timeout=130)
            started=time.monotonic()
            try:
                connection.request(method,path,payload,headers)
                response=connection.getresponse();raw=response.read();status=response.status
                return status,json.loads(raw) if raw else None,round(time.monotonic()-started,4)
            finally:connection.close()
        stopped=threading.Event();samples=[];host_guard=[]
        def monitor(process):
            while not stopped.wait(.05):
                try:
                    children=psutil.Process(process.pid).children(recursive=True)
                    rss=[p.memory_info().rss for p in children if p.is_running()]
                    samples.append({'max':max(rss,default=0),'heavy':sum(v>512*1024**2 for v in rss),'service':sum(rss)+psutil.Process(process.pid).memory_info().rss})
                    if psutil.virtual_memory().available<768*1024**2:
                        host_guard.append(True);os.killpg(process.pid,signal.SIGTERM);return
                except (psutil.NoSuchProcess,psutil.AccessDenied,ProcessLookupError):pass
        server=None;thread=None
        result={}
        result['deploymentWarnings']=deployment_warnings
        try:
            with log.open('w') as sink:
                server=subprocess.Popen([str(project/'backend/.venv/bin/gunicorn'),'--config',str(project/'deploy/gunicorn.conf.py'),'config.wsgi:application'],cwd=project,env=env,stdout=sink,stderr=sink,start_new_session=True)
                thread=threading.Thread(target=monitor,args=(server,),daemon=True);thread.start()
                for _ in range(50):
                    if server.poll() is not None:raise RuntimeError('Production server failed to start; inspect private allowlisted operations log.')
                    try:
                        if request('GET','/api/ready')[0]==200:break
                    except (OSError,http.client.HTTPException):pass
                    time.sleep(.1)
                else:raise RuntimeError('Production server readiness timed out.')
                status,_,_=request('POST','/api/documents/analyze',body,False,f'multipart/form-data; boundary={boundary}')
                assert status==401
                status,login,_=request('POST','/api/auth/login',json.dumps({'username':user.username,'password':password}),False)
                assert status==200;token=login['token'];login=password=None
                assert request('GET','/api/documents/access')[0]==204
                gate=threading.Barrier(2)
                def upload(_):
                    gate.wait(timeout=5)
                    return request('POST','/api/documents/analyze',body,content_type=f'multipart/form-data; boundary={boundary}')
                with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(upload,range(2)))
                assert sorted(r[0] for r in responses)==[200,503]
                successful=next(r for r in responses if r[0]==200)
                assert successful[1]['source']=='deterministic' and successful[1]['evidence']
                assert successful[1]['primaryDeadline'] is not None and successful[1]['primaryAmount'] is not None
                if args.small_synthetic:
                    verify_small_fields(successful[1])
                result['concurrentStatuses']=[r[0] for r in responses]
                result['coldSuccessfulSeconds']=successful[2]
                successful=responses=None
                # Close a completed upload connection before waiting for its OCR
                # response. WSGI cannot guarantee native cancellation on disconnect;
                # the existing time/RSS guard still bounds the one running job.
                headers={'Host':'api.example.test','X-Forwarded-Proto':'https','Authorization':'Token '+token,
                         'Content-Type':f'multipart/form-data; boundary={boundary}'}
                disconnected=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
                disconnected.request('POST','/api/documents/analyze',body,headers)
                time.sleep(.05);disconnected.close()
                during=request('POST','/api/documents/analyze',body,content_type=f'multipart/form-data; boundary={boundary}')
                assert during[0] in (200,503)
                result['duringDisconnectStatus']=during[0]
                deadline=time.monotonic()+30
                completed=False
                while time.monotonic()<deadline:
                    metrics=[]
                    try:
                        for line in log.read_text().splitlines():
                            value=json.loads(line)
                            if value.get('event')=='ocr':metrics.append(value)
                    except (OSError,json.JSONDecodeError):pass
                    # Cold job, a rejected busy request, then the disconnected job
                    # may be interleaved; count completed expensive jobs by duration.
                    if sum(m.get('peakRssMiB',0)>512 for m in metrics)>=2:completed=True;break
                    time.sleep(.2)
                assert completed,'Disconnected native job did not finish within bounded observation.'
                status,followup,seconds=request('POST','/api/documents/analyze',body,content_type=f'multipart/form-data; boundary={boundary}')
                assert status==200 and followup['source']=='deterministic'
                if args.small_synthetic:
                    verify_small_fields(followup)
                result['followupStatus']=status;result['warmSuccessfulSeconds']=seconds
                result['readinessStatus']=request('GET','/api/ready')[0]
                assert result['readinessStatus']==200
                assert request('POST','/api/auth/logout','{}')[0]==200
                assert request('GET','/api/auth/me')[0]==401
                token=None
        finally:
            if server and server.poll() is None:
                os.killpg(server.pid,signal.SIGTERM)
                try:server.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(server.pid,signal.SIGKILL);server.wait(timeout=5)
            stopped.set()
            if thread:thread.join(timeout=1)
            connections.close_all()
        assert not host_guard,'Stopped because host memory guard was reached.'
        assert hashlib.sha256(image.read_bytes() if image else data).digest()==original_hash
        assert (dev_database.read_bytes() if dev_database.exists() else None)==original_db
        text=log.read_text()
        assert 'synthetic.png' not in text and 'synthetic-integration-user' not in text and 'Authorization' not in text
        for line in text.splitlines():
            value=json.loads(line)
            assert set(value)<={'time','level','event','route','status','durationSeconds','peakRssMiB','code'}
        result.update(maximumHeavyProcesses=max((r['heavy'] for r in samples),default=0),
            sampledPeakProcessMiB=round(max((r['max'] for r in samples),default=0)/1024**2),
            sampledPeakServiceMiB=round(max((r['service'] for r in samples),default=0)/1024**2),
            privateTemporaryFilesRemaining=len(list((state/'tmp').iterdir())),
            originalInputUnchanged=True,developmentDatabaseUnchanged=True,allowlistedLogsOnly=True,
            authRevocationVerified=True,automaticRetries=0)
        result['workload']='480x480_synthetic_japanese' if args.small_synthetic else 'provided_synthetic_image'
        assert result['maximumHeavyProcesses']==1
        assert result['privateTemporaryFilesRemaining']==0
        output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        output.write_text(json.dumps(result,indent=2)+'\n');output.chmod(0o600)
        print(json.dumps(result))


if __name__=='__main__':main()
