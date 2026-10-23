"""Private CLI controls restricted to a marked disposable staging database."""
import json
from pathlib import Path
import re
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User,Permission
from django.utils import timezone
from rest_framework.authtoken.models import Token


def require_disposable():
    state=Path(settings.STATE_DIR)
    expected=getattr(settings,'STAGING_PROJECT',None) or __import__('os').environ.get('STAGING_PROJECT')
    marker=state/'.staging-project'
    if not expected or not re.fullmatch(r'jxtw-staging-[a-z0-9-]{6,32}',expected) or not marker.is_file() or marker.read_text().strip()!=expected:
        raise ValueError('Private QA controls require an explicitly marked disposable staging database.')
    return state


def seed(payload):
    require_disposable()
    accounts=payload['accounts']
    if len(accounts)!=2:raise ValueError('Create two bounded QA accounts.')
    permission=Permission.objects.get(content_type__app_label='models',codename='analyze_document')
    for index,item in enumerate(accounts):
        if not re.fullmatch(r'qa-[a-z0-9-]{8,40}',item['username']) or len(item['password'])<24:raise ValueError('Use generated QA-only credentials.')
        if User.objects.filter(username=item['username']).exists():raise ValueError('Existing accounts are never overwritten by QA.')
        user=User.objects.create_user(item['username'],password=item['password'],is_staff=(index==0))
        if index==0:user.user_permissions.add(permission)
    return {'accountsCreated':2}


def expire(payload):
    require_disposable()
    username=payload['username']
    if not re.fullmatch(r'qa-[a-z0-9-]{8,40}',username):raise ValueError('Use a QA account only.')
    count=Token.objects.filter(user__username=username).update(created=timezone.now()-timedelta(seconds=settings.TOKEN_TTL_SECONDS+1))
    return {'credentialsExpired':count}
