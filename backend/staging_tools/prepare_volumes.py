"""One-shot ownership/bootstrap only; no credentials, models or network loaded."""
import os
from pathlib import Path
import re


def main():
    os.umask(0o077)
    identifier=os.environ.get('STAGING_PROJECT','')
    uid,gid=int(os.environ.get('STAGING_UID','10001')),int(os.environ.get('STAGING_GID','10001'))
    if uid<=0 or gid<=0 or not re.fullmatch(r'jxtw-staging-[a-z0-9-]{6,32}',identifier):raise ValueError('Generated project/non-root UID required.')
    state=Path('/var/lib/japanxtheworld');state.mkdir(parents=True,exist_ok=True,mode=0o700)
    marker=state/'.staging-project'
    if marker.exists():
        if marker.read_text().strip()!=identifier:raise ValueError('Staging project does not own this state.')
    elif any(state.iterdir()):raise ValueError('Refusing to adopt existing non-staging state.')
    else:marker.write_text(identifier+'\n');os.chown(marker,uid,gid);marker.chmod(0o600)
    for name,mode in [('/var/lib/japanxtheworld',0o700),('/var/lib/japanxtheworld/tmp',0o700),('/opt/models',0o700),('/srv/static',0o755)]:
        path=Path(name);path.mkdir(parents=True,exist_ok=True,mode=mode);os.chown(path,uid,gid);path.chmod(mode)
    print('Private staging volume ownership prepared; no credentials copied or database migration attempted.')


if __name__=='__main__':
    try:main()
    except Exception:
        print('Private staging initialization failed; existing database rows were not changed.')
        raise SystemExit(1) from None
