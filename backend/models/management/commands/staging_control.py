"""No HTTP endpoint: operator-only disposable-data test controls."""
import json
import sys
from django.core.management.base import BaseCommand,CommandError


class Command(BaseCommand):
    def add_arguments(self,parser):parser.add_argument('action',choices=['seed','expire'])
    def handle(self,*args,**options):
        from staging_tools.control import seed,expire
        try:
            raw=sys.stdin.read(8193)
            if len(raw)>8192:raise ValueError()
            result=(seed if options['action']=='seed' else expire)(json.loads(raw))
        except Exception:raise CommandError('Disposable staging control failed. Existing non-QA data was not modified.') from None
        self.stdout.write(json.dumps(result))
