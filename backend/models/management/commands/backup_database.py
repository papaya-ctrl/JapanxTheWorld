"""Consistent SQLite snapshot; exclusive publication, private modes, no row output."""
import os
from pathlib import Path
import sqlite3
import tempfile
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create a new private SQLite backup without overwriting existing files.'

    def add_arguments(self, parser):
        parser.add_argument('destination')

    def handle(self, *args, **options):
        database = settings.DATABASES['default']
        if database['ENGINE'] != 'django.db.backends.sqlite3':
            raise CommandError('This snapshot command supports SQLite only.')
        target = Path(options['destination']).expanduser().absolute()
        parent = target.parent.resolve()
        if parent.is_relative_to(settings.BASE_DIR.parent) or parent.is_relative_to(Path(settings.STATIC_ROOT)):
            raise CommandError('Backups must be outside the source checkout and public static root.')
        temporary = None
        try:
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if parent.stat().st_mode & 0o077 or parent.stat().st_uid != os.getuid():
                raise CommandError('The backup directory must be owner-only (0700).')
            if target.exists() or target.is_symlink():
                raise CommandError('Refusing to overwrite an existing backup.')
            descriptor, temporary = tempfile.mkstemp(prefix='database-', suffix='.sqlite3', dir=parent)
            os.close(descriptor)
            source = Path(database['NAME']).resolve()
            with sqlite3.connect(source.as_uri()+'?mode=ro', uri=True) as live, sqlite3.connect(temporary) as snapshot:
                live.backup(snapshot)
                if snapshot.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise CommandError('Backup integrity verification failed.')
            os.link(temporary, target, follow_symlinks=False)
        except (OSError, sqlite3.Error):
            raise CommandError('Backup failed; existing databases and backups were not replaced.') from None
        finally:
            if temporary:
                Path(temporary).unlink(missing_ok=True)
        self.stdout.write('Backup completed and integrity verified.')
