from django.conf import settings
from django.db import models


class Document(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documents",
    )
    original_filename = models.CharField(max_length=255, null=True, blank=True)
    mime_type = models.CharField(max_length=100, null=True, blank=True)
    extracted_text = models.TextField(
        null=True,
        blank=True,
        help_text="Privacy-first: Leave null in production to avoid storing personal document text.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "models"
        db_table = "documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Document #{self.id} ({self.original_filename or 'text-input'})"


class AnalysisResult(models.Model):
    SOURCE_CHOICES = [
        ("template", "Template"),
        ("ai", "AI"),
    ]
    URGENCY_CHOICES = [
        ("low", "Low"),
        ("important", "Important"),
        ("urgent", "Urgent"),
    ]

    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name="analysis_result",
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    document_type = models.CharField(max_length=255)
    summary = models.TextField()
    deadline = models.CharField(max_length=50, null=True, blank=True)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES)
    related_guide = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "models"
        db_table = "analysis_results"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.document_type} ({self.source})"


class ChecklistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="checklist_items",
    )
    title = models.CharField(max_length=255)
    due_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "models"
        db_table = "checklist_items"
        ordering = ["completed", "due_date", "-created_at"]

    def __str__(self):
        status = "✅" if self.completed else "⬜"
        return f"{status} {self.title}"
