from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from services.trustedContent.topics_data import TRUSTED_TOPICS_DATA


@api_view(['GET'])
def guide_list(request):
    """
    GET /api/guides
    Returns all 8 trusted knowledge guides.
    """
    guides = list(TRUSTED_TOPICS_DATA.values())
    return Response(guides, status=status.HTTP_200_OK)


@api_view(['GET'])
def guide_detail(request, guide_id: str):
    """
    GET /api/guides/:id
    Returns a single trusted guide by its exact slug ID (e.g., 'residence-tax').
    """
    guide = TRUSTED_TOPICS_DATA.get(guide_id)
    if not guide:
        return Response(
            {
                "code": "GUIDE_NOT_FOUND",
                "message": f"Guide '{guide_id}' not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(guide, status=status.HTTP_200_OK)
