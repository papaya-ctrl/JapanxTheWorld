from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from middleware.file_validator import validate_uploaded_file
from services.ocr.extractor import extract_text_from_file, OCRUnreadableError
from services.documentAnalysis.analyzer import analyze_document_text
from services.documentAnalysis.persistence import save_analysis_record


def error_response(code: str, message: str, http_status: int) -> Response:
    return Response(
        {
            "code": code,
            "message": message,
        },
        status=http_status,
    )


@api_view(['GET'])
def health_check(request):
    return Response({"status": "ok"})


@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def analyze_document(request):
    raw_text = request.data.get("text", "")
    uploaded_file = request.FILES.get("file", None)

    text_str = raw_text.strip() if isinstance(raw_text, str) else ""

    if not text_str and uploaded_file is None:
        return error_response(
            code="INVALID_REQUEST",
            message="Either 'text' or 'file' must be provided.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    extracted_file_text = ""
    original_filename = None
    mime_type = None

    if uploaded_file is not None:
        is_valid, err_code, err_msg = validate_uploaded_file(uploaded_file)
        if not is_valid:
            return error_response(
                code=err_code,
                message=err_msg,
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        original_filename = uploaded_file.name
        mime_type = getattr(uploaded_file, "content_type", None)

        try:
            extracted_file_text = extract_text_from_file(uploaded_file)
        except OCRUnreadableError:
            if not text_str:
                return error_response(
                    code="OCR_UNREADABLE",
                    message="The uploaded document could not be read clearly.",
                    http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

    combined_text = f"{text_str}\n{extracted_file_text}".strip()

    try:
        result = analyze_document_text(combined_text)
        # Save metadata & analysis summary to DB (without storing personal raw text)
        save_analysis_record(
            analysis_data=result,
            user=getattr(request, "user", None),
            original_filename=original_filename,
            mime_type=mime_type,
            raw_extracted_text=combined_text,
        )
        return Response(result, status=status.HTTP_200_OK)
    except Exception:
        return error_response(
            code="AI_SERVICE_ERROR",
            message="An error occurred while analyzing the document. Please try again.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
