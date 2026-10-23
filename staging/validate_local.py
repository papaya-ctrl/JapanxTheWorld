"""Safe macOS/host fallback: actual production Django + Nginx HTTPS, synthetic QA.

This never claims Linux/container execution and never starts Docker Desktop.
"""
import argparse
from io import StringIO
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
import platform
import shutil
import psutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'backend'))
from staging.prepare import nginx_configuration,private_directory
from staging.backup import seal,restore
from staging_tools.qa_client import Transport,run


def port():
    with socket.socket() as socket_:
        socket_.bind(('127.0.0.1',0));return socket_.getsockname()[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--nginx',type=Path,required=True);parser.add_argument('--native',action='store_true');parser.add_argument('--font',type=Path);args=parser.parse_args()
    directory=private_directory(args.directory)
    manifest=json.loads((directory/'manifest.json').read_text());assert manifest['purpose']=='disposable_staging_only'
    if args.native and psutil.virtual_memory().available<3*1024**3:raise RuntimeError('Insufficient available memory for bounded native fallback QA.')
    os.umask(0o077)
    work=directory/('local-qa-'+secrets.token_hex(4));work.mkdir(mode=0o700)
    state=work/'state';state.mkdir(mode=0o700);(state/'tmp').mkdir(mode=0o700);(state/'.staging-project').write_text(manifest['project'])
    static=work/'static';static.mkdir(mode=0o755)
    body=work/'body';body.mkdir(mode=0o700)
    api_port,http_port,tls_port=port(),port(),port()
    model_root=Path.home()/'.paddlex/official_models'
    os.environ.update(DJANGO_SETTINGS_MODULE='config.settings_production',DJANGO_SECRET_KEY=(directory/'secrets/django_key').read_text().strip(),
        DJANGO_ALLOWED_HOSTS='api.staging.test',DJANGO_CORS_ALLOWED_ORIGINS=f'https://app.staging.test:{tls_port}',
        DJANGO_CSRF_TRUSTED_ORIGINS=f'https://app.staging.test:{tls_port},https://api.staging.test:{tls_port}',DJANGO_TRUSTED_PROXY_IPS='127.0.0.1,::1',
        DJANGO_STATE_DIR=str(state),DJANGO_STATIC_ROOT=str(static),DOCUMENT_OCR_MODEL_ROOT=str(model_root),STAGING_PROJECT=manifest['project'])
    import django;django.setup()
    from django.core.management import call_command
    from django.db import connections
    from staging_tools.control import seed,expire
    output=StringIO();call_command('migrate',interactive=False,stdout=output);call_command('migrate',check_unapplied=True,stdout=output)
    checks=StringIO();call_command('check',deploy=True,stdout=checks,stderr=checks)
    call_command('collectstatic',interactive=False,verbosity=0)
    accounts=[{'username':'qa-'+secrets.token_hex(6),'password':secrets.token_urlsafe(32)} for _ in range(2)]
    seed({'accounts':accounts})
    connections.close_all()
    # Build only public frontend configuration, without any backend environment.
    build_env={key:value for key,value in os.environ.items() if not key.startswith(('DJANGO_','DOCUMENT_OCR_','STAGING_','VITE_')) and key!='VERCEL'}
    build_env.update(VITE_API_BASE_URL=f'https://api.staging.test:{tls_port}/api',VITE_USE_MOCK_API='false',VITE_REQUIRE_AUTH='true')
    build=subprocess.run(['npm','run','build'],cwd=ROOT,env=build_env,capture_output=True,text=True,timeout=60)
    assert build.returncode==0,'Public frontend staging build failed.'
    for file in (ROOT/'dist').rglob('*'):
        if file.is_file() and file.suffix in {'.html','.js','.css'}:
            text=file.read_text();assert os.environ['DJANGO_SECRET_KEY'] not in text and 'BEGIN PRIVATE KEY' not in text
    configuration=nginx_configuration(https_port=tls_port,backend_port=api_port,http_port=http_port,tls_port=tls_port,
        secrets_root=str(directory/'secrets'),static_root=str(static),frontend_root=str(ROOT/'dist'),body_root=str(body),headers_file=str(directory/'headers.conf'),metrics_log=str(work/'proxy-metrics.log'),pid=str(work/'nginx.pid'))
    mime=args.nginx.resolve().parents[1]/'conf/mime.types'
    if not mime.is_file():mime=Path('/etc/nginx/mime.types')
    configuration=configuration.replace('include /etc/nginx/mime.types;',f'include {mime};')
    configuration=configuration.replace(f'listen {http_port}',f'listen 127.0.0.1:{http_port}').replace(f'listen {tls_port}',f'listen 127.0.0.1:{tls_port}')
    config=work/'nginx.conf';config.write_text(configuration)
    checked=subprocess.run([str(args.nginx),'-c',str(config),'-t','-p',str(work)+'/'],capture_output=True,text=True,timeout=10)
    assert checked.returncode==0,'Rendered staging proxy syntax validation failed.'
    stopped=threading.Event();samples=[];host_pressure=[];servers=[]
    def monitor():
        while not stopped.wait(.05):
            observed=[]
            for server in servers:
                try:observed.extend(psutil.Process(server.pid).children(recursive=True))
                except psutil.NoSuchProcess:pass
            try:
                memory=[p.memory_info().rss for p in observed if p.is_running()]
                samples.append({'peak':max(memory,default=0),'heavy':sum(value>512*1024**2 for value in memory)})
                if psutil.virtual_memory().available<768*1024**2:
                    host_pressure.append(True)
                    for server in servers:
                        if server.poll() is None:os.killpg(server.pid,signal.SIGTERM)
                    return
            except (psutil.NoSuchProcess,ProcessLookupError):pass
    thread=threading.Thread(target=monitor,daemon=True)
    report={}
    try:
        with (work/'application.log').open('w') as app_log:
            app=subprocess.Popen([str(ROOT/'backend/.venv/bin/gunicorn'),'--config',str(ROOT/'deploy/gunicorn.conf.py'),'config.wsgi:application'],cwd=ROOT,env={**os.environ,'JXTW_BIND':f'127.0.0.1:{api_port}'},stdout=app_log,stderr=app_log,start_new_session=True)
            servers.append(app)
            proxy=subprocess.Popen([str(args.nginx),'-c',str(config),'-p',str(work)+'/', '-g','daemon off;'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            servers.append(proxy);thread.start()
            transport=Transport('127.0.0.1',tls_port,directory/'secrets/ca_cert.pem')
            for _ in range(50):
                try:
                    if transport.request('GET','/api/ready',pace=False)[0]==200:break
                except OSError:pass
                time.sleep(.1)
            else:raise RuntimeError('Private local staging did not become ready.')
            # Both synthetic virtual hosts redirect to their correct local TLS port.
            redirects=[]
            for hostname in ['api.staging.test','app.staging.test']:
                connection=__import__('http.client',fromlist=['HTTPConnection']).HTTPConnection('127.0.0.1',http_port,timeout=3)
                connection.request('GET','/',headers={'Host':hostname});response=connection.getresponse();response.read()
                assert response.status==308 and response.getheader('Location')==f'https://{hostname}:{tls_port}/'
                redirects.append(response.status);connection.close()
            report=run(transport,accounts,lambda username:expire({'username':username}),native=args.native,font=args.font)
            report['httpRedirectStatuses']=redirects
            os.killpg(app.pid,signal.SIGTERM);app.wait(timeout=10)
            unavailable=transport.request('GET','/api/health')
            assert unavailable[0]==502 and 'Traceback' not in str(unavailable[1])
            assert 'evidence' not in str(unavailable[1])
            report['cases'].append({'case':'backend_unavailable','status':502,'passed':True})
    finally:
        for server in reversed(servers):
            if server.poll() is None:
                os.killpg(server.pid,signal.SIGTERM)
                try:server.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(server.pid,signal.SIGKILL);server.wait(timeout=5)
        stopped.set()
        if thread.is_alive():thread.join(timeout=1)
        connections.close_all()
    assert not host_pressure,'QA stopped at the host memory guard.'
    from models.db_models import Document,AnalysisResult
    assert Document.objects.count()==0 and AnalysisResult.objects.count()==0
    connections.close_all()
    # Validate encrypted backup/recovery on this disposable database, not dev data.
    archive=directory/'backups'/('qa-'+work.name+'.fernet');recovered=work/'restored'/'app.sqlite3'
    key=directory/'secrets/backup_key'
    seal(state/'app.sqlite3',archive,key,directory);restore(archive,recovered,key,directory)
    (recovered.parent/'tmp').mkdir(mode=0o700)
    import sqlite3
    with sqlite3.connect(recovered.as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('SELECT count(*) FROM auth_user').fetchone()[0]==2
    env={**os.environ,'DJANGO_STATE_DIR':str(recovered.parent)}
    restored_check=subprocess.run([sys.executable,str(ROOT/'backend/manage.py'),'migrate','--check','--settings=config.settings_production'],env=env,capture_output=True,text=True,timeout=15)
    assert restored_check.returncode==0,'Restored schema migration check failed.'
    verification='''
import django,json,sys
django.setup()
from django.contrib.auth import authenticate
from models.db_models import ChecklistItem
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed
from security.authentication import ExpiringTokenAuthentication
data=json.load(sys.stdin)
user=authenticate(username=data['username'],password=data['password'])
assert user and ChecklistItem.objects.filter(user=user,title='Synthetic recovery sentinel').count()==1
try:ExpiringTokenAuthentication().authenticate_credentials(Token.objects.get(user=user).key)
except AuthenticationFailed:pass
else:raise AssertionError('An expired credential was reactivated by restore.')
print('RESTORE_OK')
'''
    checked_restore=subprocess.run([sys.executable,'-c',verification],cwd=ROOT/'backend',env=env,input=json.dumps(accounts[0]),capture_output=True,text=True,timeout=15)
    assert checked_restore.returncode==0 and 'RESTORE_OK' in checked_restore.stdout,'Restored account/checklist/expiry verification failed.'
    assert (directory/'secrets/django_key').read_bytes().strip() not in recovered.read_bytes()
    assert not list(body.iterdir()) and not list((state/'tmp').iterdir())
    logs=(work/'application.log').read_text()
    for line in logs.splitlines():
        parsed=json.loads(line);assert set(parsed)<={'time','level','event','route','status','durationSeconds','peakRssMiB','code'}
    assert all(account['username'] not in logs and account['password'] not in logs for account in accounts)
    report.update(environment={'os':platform.system(),'machine':platform.machine(),'linuxContainer':False},
        maximumHeavyProcesses=max((s['heavy'] for s in samples),default=0),sampledPeakProcessMiB=round(max((s['peak'] for s in samples),default=0)/1024**2),
        containerMemoryMiB=None,encryptedBackupRestored=True,restoredMigrationsCurrent=True,serverSigningKeyExcludedFromSnapshot=True,
        temporaryDocumentFiles=0,documentRowsStored=0,restoredAuthenticationAndChecklistVerified=True,
        allowlistedApplicationLogs=True,productionHstsWarnings=['security.W005','security.W021'])
    destination=directory/'local-qa-summary.json';destination.write_text(json.dumps(report,indent=2)+'\n');destination.chmod(0o600)
    print(json.dumps(report))


if __name__=='__main__':main()
