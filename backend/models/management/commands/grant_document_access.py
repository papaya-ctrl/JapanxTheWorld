from django.contrib.auth.models import Permission, User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Explicitly grant or revoke document analysis for an existing local account.'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('--revoke', action='store_true')

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['username'])
            permission = Permission.objects.get(content_type__app_label='models', codename='analyze_document')
        except (User.DoesNotExist, Permission.DoesNotExist):
            raise CommandError('Account or permission unavailable; create the account and apply migrations first.') from None
        if options['revoke']:
            user.user_permissions.remove(permission)
        else:
            user.user_permissions.add(permission)
        self.stdout.write('Document access updated. Group and superuser permissions still apply.')
