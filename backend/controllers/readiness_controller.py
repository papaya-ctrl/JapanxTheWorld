from pathlib import Path
from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def readiness_check(request):
    try:
        executor = MigrationExecutor(connection)
        if executor.migration_plan(executor.loader.graph.leaf_nodes()):
            raise RuntimeError()
        root = Path(settings.DOCUMENT_OCR_MODEL_ROOT or Path.home()/'.paddlex/official_models')
        for name in ('PP-OCRv6_medium_det', 'PP-OCRv6_medium_rec'):
            if not all((root/name/file).is_file() for file in ('inference.yml', 'inference.pdiparams')):
                raise RuntimeError()
        if settings.PRODUCTION:
            state = Path(settings.STATE_DIR)
            if not state.is_dir() or state.stat().st_mode & 0o077:
                raise RuntimeError()
    except Exception:
        return Response({'status': 'not_ready'}, status=503, headers={'Cache-Control': 'no-store', 'Retry-After': '30'})
    return Response({'status': 'ready'}, headers={'Cache-Control': 'no-store'})
