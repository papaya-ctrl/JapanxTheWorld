"""Read runtime-mounted credentials without adding them to image/Compose ENV."""
import os
from pathlib import Path
import sys
import tempfile


def load_key(path):
    with Path(path).open(encoding='utf-8') as source:
        value=source.read(4097).strip()
    if not 50 <= len(value) <= 4096 or '\n' in value or '\x00' in value:
        raise ValueError('Invalid staging signing-key file.')
    return value


def main():
    os.umask(0o077)
    backend=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(backend))
    command=sys.argv[1:] or ['serve']
    action=command.pop(0)
    if action=='test':
        os.environ['DJANGO_SETTINGS_MODULE']='config.settings_development'
        os.environ['DJANGO_DB_PATH']=str(Path(tempfile.mkdtemp(prefix='jxtw-qa-'))/'qa.sqlite3')
        os.execv(sys.executable,[sys.executable,str(backend/'manage.py'),'test',*(command or ['tests']),'--settings=config.settings_development'])
    if action=='benchmark':
        # Does not import Django or load application credentials. The caller must
        # stop the app first; the production lease also prevents a second model.
        from staging_tools.benchmark import main as benchmark
        benchmark(command)
        return
    if action not in {'serve','manage'}:
        raise ValueError('Use serve, manage, test or benchmark.')
    os.environ['DJANGO_SECRET_KEY']=load_key(os.environ['STAGING_SECRET_FILE'])
    os.environ['DJANGO_SETTINGS_MODULE']='config.settings_production'
    if action=='manage':
        os.execv(sys.executable,[sys.executable,str(backend/'manage.py'),*command])
    import django
    django.setup()
    from django.core.management import call_command
    call_command('check',deploy=True)
    call_command('migrate',check_unapplied=True)
    # A safe static root is mounted separately; only collected code assets go here.
    call_command('collectstatic',interactive=False,verbosity=0)
    from django.conf import settings
    public=Path(settings.STATIC_ROOT)
    for path in [public,*public.rglob('*')]:
        if path.is_symlink():raise ValueError('Unexpected link in collected static files.')
        path.chmod(0o755 if path.is_dir() else 0o644)
    gunicorn=Path(sys.executable).parent/'gunicorn'
    os.execv(str(gunicorn),[str(gunicorn),'--config',str(backend.parent/'deploy/gunicorn.conf.py'),'config.wsgi:application'])


if __name__=='__main__':
    try:main()
    except Exception:
        # Configuration errors can contain filesystem/credential details. Keep the
        # entrypoint failure generic; run explicit checks privately for diagnosis.
        print('Staging startup failed. Verify private configuration and prerequisites.',file=sys.stderr)
        raise SystemExit(1) from None
