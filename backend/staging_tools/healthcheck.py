"""Private health probe: no model loading, credentials, paths or document values."""
import http.client
import sys

try:
    connection=http.client.HTTPConnection('127.0.0.1',8000,timeout=3)
    connection.request('GET','/api/ready',headers={'Host':'api.staging.test','X-Forwarded-Proto':'https'})
    response=connection.getresponse();response.read(1024);connection.close()
    sys.exit(0 if response.status==200 else 1)
except Exception:
    sys.exit(1)
