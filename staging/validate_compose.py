"""Host-side HTTPS QA against an explicitly running, disposable Linux stack."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'backend')]
from staging.run import compose
from staging_tools.qa_client import Transport,run


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--font',type=Path)
    args=parser.parse_args();os.umask(0o077)
    directory=args.directory.expanduser().resolve();base=compose(directory)
    manifest=json.loads((directory/'manifest.json').read_text())
    version=subprocess.run([*base,'exec','-T','backend','python','-c','import platform;print(platform.system(),platform.machine())'],capture_output=True,text=True,check=True,timeout=15).stdout.strip().split()
    if len(version)!=2 or version[0]!='Linux':raise RuntimeError('Expected a running Linux backend.')
    def control(action,payload):
        result=subprocess.run([*base,'exec','-T','backend','python','/app/backend/staging_tools/entrypoint.py','manage','staging_control',action],input=json.dumps(payload),capture_output=True,text=True,timeout=20)
        if result.returncode:raise RuntimeError('Private disposable staging control failed.')
    accounts=[{'username':'qa-'+secrets.token_hex(6),'password':secrets.token_urlsafe(32)} for _ in range(2)]
    control('seed',{'accounts':accounts})
    transport=Transport('127.0.0.1',manifest['httpsPort'],directory/'secrets/ca_cert.pem')
    report=run(transport,accounts,lambda username:control('expire',{'username':username}),native=True,font=args.font)
    declared=dict(line.split('=',1) for line in (directory/'compose.env').read_text().splitlines() if '=' in line)
    report['environment']={'os':version[0],'machine':version[1],'linuxContainer':True,
        'declaredHostOS':declared.get('STAGING_HOST_OS'),'declaredHostMachine':declared.get('STAGING_HOST_MACHINE'),
        'platformRequested':manifest['platform']}
    output=directory/('linux-https-qa-'+secrets.token_hex(4)+'.json')
    with output.open('x') as file:json.dump(report,file,indent=2);file.write('\n')
    output.chmod(0o600)
    print(json.dumps({'passed':report['passed'],'cases':len(report['cases']),'environment':report['environment']}))


if __name__=='__main__':main()
