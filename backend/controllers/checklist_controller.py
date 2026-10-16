from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from models.db_models import ChecklistItem
from models.serializers import ChecklistItemSerializer


@api_view(['GET', 'POST'])
def checklist_list_create(request):
    is_authed = bool(request.user and request.user.is_authenticated)

    if request.method == 'GET':
        if is_authed:
            items = ChecklistItem.objects.filter(user=request.user)
        else:
            items = ChecklistItem.objects.filter(user__isnull=True)
        serializer = ChecklistItemSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = ChecklistItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user if is_authed else None)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH', 'DELETE'])
def checklist_detail_update_delete(request, pk):
    is_authed = bool(request.user and request.user.is_authenticated)
    try:
        if is_authed:
            item = ChecklistItem.objects.get(pk=pk, user=request.user)
        else:
            item = ChecklistItem.objects.get(pk=pk, user__isnull=True)
    except ChecklistItem.DoesNotExist:
        return Response(
            {"code": "NOT_FOUND", "message": "Checklist item not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == 'PATCH':
        serializer = ChecklistItemSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        item.delete()
        return Response({"message": "Checklist item deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
