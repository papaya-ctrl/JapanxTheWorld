import { useState } from "react";
import type { DocumentInputFormValues } from "../types";

type DocumentInputFormProps = {
  initialValue?: DocumentInputFormValues;
  onSubmit: (values: DocumentInputFormValues) => Promise<void> | void;
  onRetry?: () => Promise<void> | void;
  isSubmitting: boolean;
  errorMessage?: string;
};

export function DocumentInputForm({
  initialValue,
  onSubmit,
  onRetry,
  isSubmitting,
  errorMessage,
}: DocumentInputFormProps) {
  const [values, setValues] = useState<DocumentInputFormValues>({
    documentText: initialValue?.documentText ?? "",
    documentTypeHint: initialValue?.documentTypeHint ?? "",
    sourceLanguageHint: initialValue?.sourceLanguageHint ?? "ja",
  });
  const [validationError, setValidationError] = useState<string>("");

  const handleChange = (
    field: keyof DocumentInputFormValues,
    value: string,
  ) => {
    setValues((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const applySample = () => {
    setValues({
      documentText:
        "住民税のお知らせです。納期限までにお支払いください。お問い合わせは市役所へお願いします。",
      documentTypeHint: "tax notice",
      sourceLanguageHint: "ja",
    });
    setValidationError("");
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!values.documentText.trim()) {
      setValidationError("Please paste document text before starting analysis.");
      return;
    }

    setValidationError("");
    await onSubmit(values);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-6 rounded-[32px] border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60 sm:p-8"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">
            Start document analysis
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Paste the document text below. A document type hint is optional.
          </p>
        </div>
        <button
          type="button"
          onClick={applySample}
          className="inline-flex rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
        >
          Try sample text
        </button>
      </div>

      <div className="grid gap-5">
        <div className="grid gap-2">
          <label htmlFor="documentText" className="text-sm font-medium text-slate-800">
            Document text
          </label>
          <textarea
            id="documentText"
            value={values.documentText}
            onChange={(event) => handleChange("documentText", event.target.value)}
            rows={9}
            aria-invalid={Boolean(validationError)}
            aria-describedby={
              validationError ? "documentText-error" : "documentText-helper"
            }
            className="rounded-3xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-900 outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
            placeholder="Paste Japanese document text here"
          />
          <span id="documentText-helper" className="text-xs text-slate-500">
            Synthetic or copied text works in mock mode. Avoid highly sensitive
            private details.
          </span>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div className="grid gap-2">
            <label htmlFor="documentTypeHint" className="text-sm font-medium text-slate-800">
              Document type hint
            </label>
            <input
              id="documentTypeHint"
              value={values.documentTypeHint}
              onChange={(event) =>
                handleChange("documentTypeHint", event.target.value)
              }
              className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
              placeholder="Example: tax notice"
            />
          </div>

          <div className="grid gap-2">
            <label htmlFor="sourceLanguageHint" className="text-sm font-medium text-slate-800">
              Source language hint
            </label>
            <select
              id="sourceLanguageHint"
              value={values.sourceLanguageHint}
              onChange={(event) =>
                handleChange("sourceLanguageHint", event.target.value)
              }
              className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
            >
              <option value="ja">Japanese</option>
              <option value="en">English</option>
              <option value="mixed">Mixed</option>
            </select>
          </div>
        </div>
      </div>

      {validationError ? (
        <p
          id="documentText-error"
          role="alert"
          className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {validationError}
        </p>
      ) : null}

      {errorMessage ? (
        <div
          role="alert"
          aria-live="assertive"
          className="space-y-3 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          <p>{errorMessage}</p>
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              disabled={isSubmitting}
              className="inline-flex rounded-full border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Retry analysis
            </button>
          ) : null}
        </div>
      ) : null}

      <div aria-live="polite" className="min-h-6 text-sm font-medium text-blue-700">
        {isSubmitting ? "Analyzing document..." : ""}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs leading-5 text-slate-500">
          This tool uses simple English and may not capture every detail. Please
          confirm important actions with official sources.
        </p>
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center justify-center rounded-full bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
        >
          {isSubmitting ? "Analyzing..." : "Analyze document"}
        </button>
      </div>
    </form>
  );
}
