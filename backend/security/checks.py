"""Deployment checks inspect prerequisites without loading OCR or writing state."""
import os
from pathlib import Path
from django.conf import settings
from django.core.checks import Error, register, Tags


@register(Tags.security, deploy=True)
def private_runtime_paths(app_configs, **kwargs):
    if not getattr(settings, 'PRODUCTION', False): return []
    errors = []
    state = Path(settings.STATE_DIR)
    if not state.is_dir() or state.stat().st_mode & 0o077 or state.stat().st_uid != os.getuid():
        errors.append(Error('Production state must exist and be owner-only (0700) for the application account.', id='jxtw.E001'))
    temporary = Path(settings.FILE_UPLOAD_TEMP_DIR)
    if not temporary.is_dir() or temporary.stat().st_mode & 0o077 or temporary.stat().st_uid != os.getuid():
        errors.append(Error('The private temporary directory must exist with owner-only access (0700).', id='jxtw.E003'))
    database = Path(settings.DATABASES['default']['NAME'])
    if database.exists() and (database.stat().st_mode & 0o077 or database.stat().st_uid != os.getuid()):
        errors.append(Error('The production database must be owned by the application account with mode 0600.', id='jxtw.E004'))
    for name in ('PP-OCRv6_medium_det', 'PP-OCRv6_medium_rec'):
        if not all((Path(settings.DOCUMENT_OCR_MODEL_ROOT)/name/file).is_file() for file in ('inference.yml', 'inference.pdiparams')):
            errors.append(Error('Install the selected local Medium OCR models before serving uploads.', id='jxtw.E002'))
            break
    return errors
