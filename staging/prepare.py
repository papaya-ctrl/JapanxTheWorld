"""Generate staging-only credentials/configuration outside Git; never starts Docker."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def private_directory(value):
    directory=Path(value).expanduser().resolve()
    if directory.is_relative_to(ROOT):raise ValueError('Staging secrets/state must be outside the checkout.')
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+',str(directory)):raise ValueError('Use a simple private directory path for Compose and Nginx files.')
    return directory


def nginx_configuration(*,https_port=18443,backend_port=8000,http_port=8080,tls_port=8443,
                        secrets_root='/run/secrets',static_root='/srv/static',
                        frontend_root='/srv/frontend',body_root='/var/cache/nginx/body',
                        headers_file='/etc/nginx/snippets/jxtw-headers.conf',metrics_log='/dev/stdout',pid='/tmp/nginx.pid'):
    if not all(1024<=value<=65535 for value in [https_port,backend_port,http_port,tls_port]):raise ValueError('Use bounded unprivileged ports.')
    source=(ROOT/'deploy/nginx.conf.example').read_text()
    replacements={
        "'https://app.example.invalid'":f"'https://app.staging.test:{https_port}'",
        'listen 80 default_server;':f'listen {http_port} default_server;',
        'listen 80;':f'listen {http_port};', 'listen 443 ssl;':f'listen {tls_port} ssl;',
        '/etc/letsencrypt/live/api.example.invalid/fullchain.pem':secrets_root+'/tls_cert.pem',
        '/etc/letsencrypt/live/api.example.invalid/privkey.pem':secrets_root+'/tls_key.pem',
        '/var/log/nginx/jxtw-metrics.log':metrics_log,
        '/var/lib/nginx/jxtw-body':body_root,
        '/etc/nginx/snippets/jxtw-headers.conf':headers_file,
        '/srv/japanxtheworld-static/':static_root.rstrip('/')+'/',
        '127.0.0.1:8000':f'127.0.0.1:{backend_port}',
        'https://api.example.invalid$request_uri':f'https://api.staging.test:{https_port}$request_uri',
        'api.example.invalid':'api.staging.test',
    }
    for old,new in replacements.items():source=source.replace(old,new)
    # Staging never installs HSTS for an unverified public domain. Django retains
    # its short host-only policy, with documented W005/W021 warnings unchanged.
    frontend=f'''
server {{
    listen {http_port};
    server_name app.staging.test;
    access_log off;
    location / {{ return 308 https://app.staging.test:{https_port}$request_uri; }}
}}
server {{
    listen {tls_port} ssl;
    server_name app.staging.test;
    ssl_certificate {secrets_root}/tls_cert.pem;
    ssl_certificate_key {secrets_root}/tls_key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_tickets off;
    server_tokens off;
    access_log {metrics_log} jxtw_metrics;
    if ($host != app.staging.test) {{ return 444; }}
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy no-referrer always;
    add_header X-Frame-Options DENY always;
    add_header Cache-Control no-store always;
    add_header Permissions-Policy 'camera=(), microphone=(), geolocation=()' always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self' https://api.staging.test:{https_port}; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'" always;
    root {frontend_root};
    location / {{ try_files $uri $uri/ /index.html; }}
}}
server {{ listen 127.0.0.1:8081; access_log off; location / {{ return 200 'ok'; }} }}
'''
    return f'pid {pid};\nerror_log /dev/null crit;\nevents {{ worker_connections 64; }}\nhttp {{\ninclude /etc/nginx/mime.types;\ndefault_type application/octet-stream;\n'+source+frontend+'\n}\n'


def prepare(directory,*,openssl=None,http_port=18080,https_port=18443,target='linux/amd64',uid=None,gid=None):
    directory=private_directory(directory)
    if directory.exists():raise FileExistsError('Use a new private directory; existing credentials are never overwritten.')
    if target not in {'linux/amd64','linux/arm64'}:raise ValueError('Select a Linux CPU platform explicitly.')
    uid,gid=uid if uid is not None else os.getuid(),gid if gid is not None else os.getgid()
    if uid<=0 or gid<=0:raise ValueError('Choose an explicit non-root --uid/--gid when preparing as root.')
    if not 1024<=http_port<=65535 or not 1024<=https_port<=65535 or http_port==https_port:raise ValueError('Use distinct unprivileged ports.')
    tool=openssl or shutil.which('openssl')
    if not tool:raise FileNotFoundError('Install an OpenSSL CLI for disposable local TLS.')
    os.umask(0o077)
    directory.mkdir(parents=True,mode=0o700)
    (directory/'benchmark-inputs').mkdir(mode=0o700)
    if os.getuid()==0:os.chown(directory/'benchmark-inputs',uid,gid)
    private=directory/'secrets';private.mkdir(mode=0o700)
    (private/'django_key').write_text(secrets.token_urlsafe(64)+'\n')
    from cryptography.fernet import Fernet
    (private/'backup_key').write_bytes(Fernet.generate_key()+b'\n')
    commands=[
        [tool,'req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(private/'ca_key.pem'),'-out',str(private/'ca_cert.pem'),'-days','2','-subj','/CN=JapanxTheWorld Disposable Staging CA','-addext','basicConstraints=critical,CA:TRUE'],
        [tool,'req','-new','-newkey','rsa:2048','-nodes','-keyout',str(private/'tls_key.pem'),'-out',str(private/'tls.csr'),'-subj','/CN=api.staging.test'],
    ]
    extension=private/'tls.ext';extension.write_text('subjectAltName=DNS:api.staging.test,DNS:app.staging.test\nbasicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n')
    commands.append([tool,'x509','-req','-in',str(private/'tls.csr'),'-CA',str(private/'ca_cert.pem'),'-CAkey',str(private/'ca_key.pem'),'-CAcreateserial','-out',str(private/'tls_cert.pem'),'-days','2','-extfile',str(extension)])
    for command in commands:
        process=subprocess.run(command,capture_output=True,timeout=20)
        if process.returncode:raise RuntimeError('Disposable certificate generation failed. Existing credentials were not replaced.')
    for file in private.iterdir():
        file.chmod(0o600)
        if os.getuid()==0:os.chown(file,uid,gid)
    (directory/'nginx.conf').write_text(nginx_configuration(https_port=https_port))
    (directory/'headers.conf').write_text((ROOT/'deploy/nginx-security-headers.conf.example').read_text())
    for name in ('nginx.conf','headers.conf'):(directory/name).chmod(0o644)
    identifier='jxtw-staging-'+secrets.token_hex(4)
    # Only public values and private file locations go into this env file.
    values={'STAGING_PROJECT':identifier,'STAGING_DIRECTORY':str(directory),'STAGING_HTTP_PORT':http_port,'STAGING_HTTPS_PORT':https_port,'STAGING_PLATFORM':target,'STAGING_HOST_MACHINE':platform.machine(),'STAGING_HOST_OS':platform.system(),'STAGING_UID':uid,'STAGING_GID':gid}
    (directory/'compose.env').write_text(''.join(f'{key}={value}\n' for key,value in values.items()))
    (directory/'manifest.json').write_text(json.dumps({'schemaVersion':1,'purpose':'disposable_staging_only','project':identifier,'platform':target,'httpPort':http_port,'httpsPort':https_port,'secretsIncluded':False},indent=2)+'\n')
    return directory/'compose.env'


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory');parser.add_argument('--openssl');parser.add_argument('--http-port',type=int,default=18080);parser.add_argument('--https-port',type=int,default=18443);parser.add_argument('--platform',default='linux/amd64');parser.add_argument('--uid',type=int);parser.add_argument('--gid',type=int)
    args=parser.parse_args()
    prepare(args.directory,openssl=args.openssl,http_port=args.http_port,https_port=args.https_port,target=args.platform,uid=args.uid,gid=args.gid)
    print('Private staging-only credentials and Compose configuration generated; no services started.')
