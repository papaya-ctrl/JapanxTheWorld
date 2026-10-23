"""Guarded Compose commands. Never starts Docker Desktop or removes volumes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from staging.preflight import inspect
from staging.prepare import private_directory


def compose(directory):
    directory=private_directory(directory)
    manifest=json.loads((directory/'manifest.json').read_text())
    if manifest.get('purpose')!='disposable_staging_only':raise ValueError('Use prepared disposable staging only.')
    return ['docker','compose','--env-file',str(directory/'compose.env'),'-f',str(ROOT/'staging/compose.yaml')]


def execute(command,**kwargs):
    return subprocess.run(command,check=True,**kwargs)


def require_idle(base):
    running=execute([*base,'ps','--status','running','--services'],capture_output=True,text=True).stdout.splitlines()
    if any(name in running for name in ['backend','proxy','benchmark','qa','model-setup']):
        raise RuntimeError('Stop this staging stack before isolated tests, models, migration or benchmarks.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--private-input',help='Existing filename inside the private benchmark-inputs directory; benchmark only.')
    parser.add_argument('action',choices=['config','build','initialize','models','migrate','up','status','stop','test','benchmark','recycling'])
    args=parser.parse_args();args.directory=private_directory(args.directory);base=compose(args.directory)
    if args.private_input:
        if args.action!='benchmark' or Path(args.private_input).name!=args.private_input:raise ValueError('Use a filename inside benchmark-inputs with benchmark only.')
        path=(args.directory/'benchmark-inputs'/args.private_input).resolve()
        if not path.is_file() or not path.is_relative_to((args.directory/'benchmark-inputs').resolve()):raise ValueError('Expected an existing private input.')
    if args.action=='config':execute([*base,'config','--quiet']);return
    if args.action not in {'status','stop'}:
        preflight=inspect()
        if not preflight['linuxExecutionAllowed']:
            print(json.dumps(preflight,indent=2));raise SystemExit(3)
    if args.action=='status':execute([*base,'ps']);return
    if args.action=='stop':execute([*base,'stop']);return
    if args.action in {'build','initialize','models','migrate','test','benchmark','recycling'}:require_idle(base)
    commands={
        'build':['--profile','setup','--profile','qa','build','backend','proxy','model-setup','qa'],
        'initialize':['--profile','setup','run','--rm','--no-deps','prepare'],
        'models':['--profile','setup','run','--rm','--no-deps','model-setup'],
        'migrate':['run','--rm','--no-deps','backend','manage','migrate','--noinput'],
        'up':['up','-d','--no-build','backend','proxy'],
        'test':['--profile','qa','run','--rm','--no-deps','qa'],
        'benchmark':['--profile','benchmark','run','--rm','--no-deps','benchmark'],
        'recycling':['--profile','benchmark','run','--rm','--no-deps','benchmark','benchmark','--small-synthetic','--repeat','3','--verify-recycling'],
    }
    selected=commands[args.action]
    if args.private_input:selected=[*selected,'benchmark','--private-input','/private-inputs/'+args.private_input,'--repeat','3']
    execute([*base,*selected])


if __name__=='__main__':main()
