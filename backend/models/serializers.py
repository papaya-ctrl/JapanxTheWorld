from rest_framework import serializers
from models.db_models import ChecklistItem

class ChecklistItemSerializer(serializers.ModelSerializer):
    dueDate = serializers.DateField(source='due_date', required=False, allow_null=True)

    class Meta:
        model = ChecklistItem
        fields = ['id', 'title', 'dueDate', 'completed', 'created_at']
        read_only_fields = ['id', 'created_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Frontend သုံးရန် dueDate format ကို YYYY-MM-DD ဖြင့် အတိအကျ ပို့ပေးသည်
        if instance.due_date:
            ret['dueDate'] = instance.due_date.strftime('%Y-%m-%d')
        else:
            ret['dueDate'] = None
        return ret
