from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from services.trustedContent.resources_data import OFFICIAL_RESOURCES_DATA


@api_view(['GET'])
def resource_list(request):
    """
    GET /api/resources
    Returns official Help Center links and hotlines.
    Supports optional ?category= query parameter.
    """
    category = request.query_params.get("category", "").strip().lower()
    if category:
        filtered = [r for r in OFFICIAL_RESOURCES_DATA if r["category"].lower() == category]
        return Response(filtered, status=status.HTTP_200_OK)

    return Response(OFFICIAL_RESOURCES_DATA, status=status.HTTP_200_OK)
