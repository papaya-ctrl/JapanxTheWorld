"""Validate the proxy templates on loopback with disposable TLS and a fake API.

No Django users, real documents, model loads, system config or cloud deployment.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import signal
import socket
import ssl
import subprocess
import tempfile
import threading
import time


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));return listener.getsockname()[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--nginx',type=Path,required=True)
    parser.add_argument('--openssl',type=Path,default=Path('/opt/homebrew/opt/openssl@3/bin/openssl'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();project=Path(__file__).resolve().parents[1]
    output=args.output.expanduser().resolve()
    if output.is_relative_to(project):raise ValueError('Keep local proxy artifacts outside the source checkout.')
    entered=threading.Event();release=threading.Event();hold=threading.Event()
    calls={'access':0,'post':0};captured=[]
    class API(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            calls['access']+=1
            authorization=self.headers.get('Authorization')
            status=204 if authorization=='Token synthetic-authorized' else 403 if authorization else 401
            self.send_response(status)
            if status==401:self.send_header('WWW-Authenticate','Token')
            self.send_header('Content-Length','0');self.end_headers()
        def do_POST(self):
            calls['post']+=1
            self.rfile.read(int(self.headers.get('Content-Length',0)))
            captured.append({'realIp':self.headers.get('X-Real-IP'),'proto':self.headers.get('X-Forwarded-Proto'),'forwarded':self.headers.get('X-Forwarded-For')})
            if hold.is_set():entered.set();release.wait(timeout=5)
            body=b'{"status":"synthetic_ok"}'
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Access-Control-Allow-Origin','https://app.example.invalid')
            self.end_headers();self.wfile.write(body)
    api=ThreadingHTTPServer(('127.0.0.1',0),API)
    api_thread=threading.Thread(target=api.serve_forever,daemon=True);api_thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix='jxtw-proxy-smoke-') as directory:
            root=Path(directory);(root/'logs').mkdir();(root/'body').mkdir(mode=0o700);(root/'static').mkdir()
            cert=root/'cert.pem';key=root/'key.pem'
            generated=subprocess.run([str(args.openssl),'req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=api.example.invalid','-addext','subjectAltName=DNS:api.example.invalid'],capture_output=True,timeout=15)
            assert generated.returncode==0,'Disposable certificate generation failed.'
            key.chmod(0o600)
            http_port,tls_port=free_port(),free_port()
            template=(project/'deploy/nginx.conf.example').read_text()
            replacements={
                'listen 80 default_server;':f'listen 127.0.0.1:{http_port} default_server;',
                'listen 80;':f'listen 127.0.0.1:{http_port};',
                'listen 443 ssl;':f'listen 127.0.0.1:{tls_port} ssl;',
                '/etc/letsencrypt/live/api.example.invalid/fullchain.pem':str(cert),
                '/etc/letsencrypt/live/api.example.invalid/privkey.pem':str(key),
                '/etc/nginx/snippets/jxtw-headers.conf':str(root/'headers.conf'),
                '/var/log/nginx/jxtw-metrics.log':str(root/'metrics.log'),
                '/var/lib/nginx/jxtw-body':str(root/'body'),
                '/srv/japanxtheworld-static/':str(root/'static')+'/',
                '127.0.0.1:8000':f'127.0.0.1:{api.server_port}',
            }
            for old,new in replacements.items():template=template.replace(old,new)
            (root/'headers.conf').write_text((project/'deploy/nginx-security-headers.conf.example').read_text())
            prefix=f'pid {root}/nginx.pid;\nerror_log {root}/logs/main.log crit;\nevents {{ worker_connections 32; }}\nhttp {{\n'
            config=root/'nginx.conf';config.write_text(prefix+template+'\n}\n')
            checked=subprocess.run([str(args.nginx),'-p',str(root)+'/', '-c',str(config),'-t'],capture_output=True,text=True,timeout=10)
            if checked.returncode:raise RuntimeError('Prepared Nginx configuration failed syntax validation: '+checked.stderr)
            context=ssl.create_default_context(cafile=str(cert))
            class LocalTLS(http.client.HTTPSConnection):
                def connect(self):
                    plain=socket.create_connection(('127.0.0.1',tls_port),timeout=self.timeout)
                    self.sock=context.wrap_socket(plain,server_hostname='api.example.invalid')
            def request(method='POST',*,authorization=None,body=b'x',origin='https://app.example.invalid',length=None,host='api.example.invalid'):
                conn=LocalTLS('api.example.invalid',timeout=5)
                try:
                    headers={'Host':host,'Origin':origin,'X-Real-IP':'192.0.2.99','X-Forwarded-For':'192.0.2.98','X-Forwarded-Proto':'http'}
                    if authorization:headers['Authorization']=authorization
                    if length is not None:
                        conn.putrequest(method,'/api/documents/analyze',skip_host=True)
                        for name,value in {**headers,'Content-Length':str(length)}.items():conn.putheader(name,value)
                        conn.endheaders()
                    else:conn.request(method,'/api/documents/analyze',body,headers)
                    response=conn.getresponse();data=response.read()
                    return response.status,response.getheaders(),json.loads(data) if data else None
                finally:conn.close()
            process=None
            def start(functional=False):
                nonlocal process
                # Functional cases isolate CORS/auth/concurrency from rate timing.
                # The original exact production rate is tested in a fresh process.
                text=template.replace('rate=12r/m','rate=1000r/s') if functional else template
                config.write_text(prefix+text+'\n}\n')
                process=subprocess.Popen([str(args.nginx),'-p',str(root)+'/', '-c',str(config),'-g','daemon off;'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                for _ in range(50):
                    if process.poll() is not None:raise RuntimeError('Local Nginx failed to start.')
                    try:
                        with socket.create_connection(('127.0.0.1',tls_port),timeout=.1):return
                    except OSError:time.sleep(.02)
                raise RuntimeError('Local proxy startup timed out.')
            def stop():
                nonlocal process
                if process and process.poll() is None:
                    process.send_signal(signal.SIGTERM)
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=2)
                process=None
            result={'syntaxCheck':True,'tlsCertificateVerified':True}
            try:
                start(functional=True)
                before=calls.copy()
                preflight=request('OPTIONS',body=None)
                assert preflight[0]==204 and calls==before
                assert dict(preflight[1])['Access-Control-Allow-Origin']=='https://app.example.invalid'
                forbidden_origin=request('OPTIONS',body=None,origin='https://evil.example.invalid')
                assert 'Access-Control-Allow-Origin' not in dict(forbidden_origin[1])
                denied=request(length=1024*1024)
                assert denied[0]==401 and denied[2]['code']=='AUTH_REQUIRED' and calls['post']==0
                assert dict(denied[1])['Access-Control-Allow-Origin']=='https://app.example.invalid'
                forbidden=request(authorization='Token synthetic-forbidden',length=1024*1024)
                assert forbidden[0]==403 and calls['post']==0
                oversized=request(authorization='Token synthetic-authorized',length=11*1024**2)
                assert oversized[0]==413 and oversized[2]['code']=='FILE_TOO_LARGE' and calls['post']==0
                hold.set()
                with ThreadPoolExecutor(max_workers=1) as pool:
                    pending=pool.submit(request,authorization='Token synthetic-authorized')
                    assert entered.wait(timeout=3)
                    busy=request(authorization='Token synthetic-authorized')
                    assert busy[0]==503 and busy[2]['code']=='SERVICE_BUSY'
                    release.set();accepted=pending.result(timeout=5)
                assert accepted[0]==200 and calls['post']==1
                assert [value for name,value in accepted[1] if name.lower()=='access-control-allow-origin']==['https://app.example.invalid']
                assert captured==[{'realIp':'127.0.0.1','proto':'https','forwarded':None}]
                result.update(preflightStatus=204,unauthorizedBeforeBodyStatus=401,forbiddenBeforeBodyStatus=403,
                    oversizedBeforeBodyStatus=413,concurrentStatuses=[200,503],trustedHeadersOverwritten=True,
                    allowedOriginHeaderCount=1,temporaryBodyFiles=len(list((root/'body').iterdir())))
                stop();start(functional=False)
                statuses=[request(length=1024*1024)[0] for _ in range(3)]
                assert statuses==[401,401,429]
                result['exactProductionRateStatuses']=statuses
            finally:release.set();stop()
            metrics=(root/'metrics.log').read_text()
            assert all(all(character.isdigit() or character in ' .-\n' for character in line) for line in metrics.splitlines())
            assert not list((root/'body').iterdir())
            result['numericLogsOnly']=True
            output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            output.write_text(json.dumps(result,indent=2)+'\n');output.chmod(0o600)
            print(json.dumps(result))
    finally:release.set();api.shutdown();api.server_close();api_thread.join(timeout=1)


if __name__=='__main__':main()
