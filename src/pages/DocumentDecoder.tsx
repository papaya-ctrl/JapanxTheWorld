import { startTransition, useState } from "react";
import { useNavigate } from "react-router";
import { DocumentInputForm } from "../components/DocumentInputForm";
import { analyzeDocument } from "../api/client";
import type { ApiError, DocumentAnalysisResult, DocumentInputFormValues } from "../types";

const PRIVACY_WARNING =
  "Do not upload highly sensitive personal information unless you understand how the service will process it. If your document includes private details, confirm whether it is safe to share before submitting.";

export function DocumentDecoder() {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [lastSubmittedValues, setLastSubmittedValues] =
    useState<DocumentInputFormValues | null>(null);

  const handleSubmit = async (values: DocumentInputFormValues) => {
    setIsSubmitting(true);
    setErrorMessage("");
    setLastSubmittedValues(values);

    try {
      const result: DocumentAnalysisResult = await analyzeDocument(values);
      window.sessionStorage.setItem(
        "japanxtheworld.lastAnalysis",
        JSON.stringify(result),
      );
      startTransition(() => {
        navigate("/document-decoder/result", { state: { result } });
      });
    } catch (error) {
      const apiError = error as ApiError;
      setErrorMessage(
        apiError.message ||
          "The analysis could not be completed. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRetry = async () => {
    if (!lastSubmittedValues) {
      return;
    }

    await handleSubmit(lastSubmittedValues);
  };

  return (
    <div className="space-y-8">
      <section className="grid gap-6 rounded-[36px] bg-gradient-to-br from-white to-blue-50 px-6 py-8 ring-1 ring-slate-200 sm:px-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4">
          <span className="inline-flex rounded-full bg-blue-100 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-blue-700">
            Document Decoder
          </span>
          <h1 className="text-3xl font-semibold text-slate-900 sm:text-4xl">
            Understand a Japanese document step by step
          </h1>
          <p className="max-w-2xl text-sm leading-7 text-slate-600">
            Upload a photo, PDF, or paste document text to receive a structured
            explanation in simple English. The result will show the summary,
            urgency, important points, and practical next steps.
          </p>
        </div>
        <div className="rounded-[28px] border border-red-100 bg-red-50 p-5">
          <p className="text-sm font-semibold text-red-700">Privacy warning</p>
          <p className="mt-3 text-sm leading-6 text-red-700/90">
            {PRIVACY_WARNING}
          </p>
        </div>
      </section>

      <DocumentInputForm
        onSubmit={handleSubmit}
        onRetry={lastSubmittedValues ? handleRetry : undefined}
        isSubmitting={isSubmitting}
        errorMessage={errorMessage}
      />
    </div>
  );
}
