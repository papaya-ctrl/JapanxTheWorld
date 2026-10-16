import {
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import type { DocumentFileInput, DocumentInputFormValues } from "../types";

type DocumentInputFormProps = {
  initialValue?: DocumentInputFormValues;
  onSubmit: (values: DocumentInputFormValues) => Promise<void> | void;
  onRetry?: () => Promise<void> | void;
  isSubmitting: boolean;
  errorMessage?: string;
};

const ACCEPTED_FILE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/pdf",
] as const;
const ACCEPTED_FILE_INPUT = ACCEPTED_FILE_TYPES.join(",");
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

const formatFileSize = (size: number) => {
  if (size < 1024 * 1024) {
    return `${Math.max(1, Math.round(size / 1024))} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
};

const isAcceptedFileType = (type: string) =>
  ACCEPTED_FILE_TYPES.some((acceptedType) => acceptedType === type);

const isImageFile = (type: string) => type.startsWith("image/");

export function DocumentInputForm({
  initialValue,
  onSubmit,
  onRetry,
  isSubmitting,
  errorMessage,
}: DocumentInputFormProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [values, setValues] = useState<DocumentInputFormValues>({
    documentText: initialValue?.documentText ?? "",
    documentFile: initialValue?.documentFile,
    documentTypeHint: initialValue?.documentTypeHint ?? "",
    sourceLanguageHint: initialValue?.sourceLanguageHint ?? "ja",
  });
  const [validationError, setValidationError] = useState<string>("");
  const [isDragging, setIsDragging] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string>("");

  useEffect(() => {
    if (
      values.documentFile &&
      isImageFile(values.documentFile.type) &&
      typeof URL.createObjectURL === "function"
    ) {
      const nextPreviewUrl = URL.createObjectURL(values.documentFile.file);
      setPreviewUrl(nextPreviewUrl);

      return () => URL.revokeObjectURL(nextPreviewUrl);
    }

    setPreviewUrl("");
    return undefined;
  }, [values.documentFile]);

  const handleChange = (
    field: "documentText" | "documentTypeHint" | "sourceLanguageHint",
    value: string,
  ) => {
    setValues((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const applySample = () => {
    setValues((current) => ({
      ...current,
      documentText:
        "住民税のお知らせです。納期限までにお支払いください。お問い合わせは市役所へお願いします。",
      documentTypeHint: "tax notice",
      sourceLanguageHint: "ja",
    }));
    setValidationError("");
  };

  const resetFileInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const removeSelectedFile = () => {
    setValues((current) => ({
      ...current,
      documentFile: undefined,
    }));
    setValidationError("");
    resetFileInput();
  };

  const selectFile = (file: File | undefined) => {
    if (!file) {
      return;
    }

    if (!isAcceptedFileType(file.type)) {
      setValidationError("Please upload a JPEG, PNG, WebP, or PDF file.");
      resetFileInput();
      return;
    }

    if (file.size === 0) {
      setValidationError("This file is empty. Please choose another file.");
      resetFileInput();
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setValidationError("Please choose a file smaller than 10 MB.");
      resetFileInput();
      return;
    }

    const documentFile: DocumentFileInput = {
      file,
      name: file.name,
      type: file.type,
      size: file.size,
    };

    setValues((current) => ({
      ...current,
      documentFile,
    }));
    setValidationError("");
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    selectFile(event.target.files?.[0]);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    selectFile(event.dataTransfer.files[0]);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const hasText = values.documentText.trim().length > 0;
    const hasFile = Boolean(values.documentFile);

    if (!hasText && !hasFile) {
      setValidationError(
        "Please paste document text or choose a supported document file.",
      );
      return;
    }

    setValidationError("");
    await onSubmit(values);
  };

  const selectedFile = values.documentFile;
  const selectedFileFallbackLabel =
    selectedFile && isImageFile(selectedFile.type) ? "IMG" : "PDF";

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
            Upload a photo, document, or PDF, or paste document text below.
          </p>
        </div>
        <button
          type="button"
          onClick={applySample}
          className="inline-flex rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
        >
          Try sample text
        </button>
      </div>

      <div className="grid gap-5">
        <div className="grid gap-3">
          <div className="flex items-center justify-between gap-3">
            <label htmlFor="documentFile" className="text-sm font-medium text-slate-800">
              Upload Photo / Document
            </label>
            <span className="text-xs text-slate-500">Max 10 MB</span>
          </div>

          <div
            onDragEnter={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragOver={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            className={[
              "rounded-[28px] border border-dashed p-4 transition sm:p-5",
              isDragging
                ? "border-blue-400 bg-blue-50"
                : "border-slate-300 bg-slate-50",
            ].join(" ")}
          >
            <input
              ref={fileInputRef}
              id="documentFile"
              type="file"
              accept={ACCEPTED_FILE_INPUT}
              aria-label="Upload Photo / Document"
              onChange={handleFileChange}
              className="sr-only"
            />

            {selectedFile ? (
              <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                <div className="flex gap-4">
                  {previewUrl ? (
                    <img
                      src={previewUrl}
                      alt="Selected document preview"
                      className="h-24 w-24 rounded-2xl border border-slate-200 object-cover"
                    />
                  ) : (
                    <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-2xl border border-red-100 bg-red-50 text-sm font-semibold text-red-700">
                      {selectedFileFallbackLabel}
                    </div>
                  )}

                  <div className="min-w-0 space-y-2">
                    <p className="truncate text-sm font-semibold text-slate-900">
                      {selectedFile.name}
                    </p>
                    <p className="text-sm text-slate-600">
                      {selectedFile.type} · {formatFileSize(selectedFile.size)}
                    </p>
                    <p className="text-xs leading-5 text-blue-700">
                      Mock mode: files are not OCR-read yet. The demo result uses
                      mock analysis so the UI can be tested now.
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                  >
                    Replace
                  </button>
                  <button
                    type="button"
                    onClick={removeSelectedFile}
                    className="rounded-full border border-red-200 bg-white px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600"
                  >
                    Remove file
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-900">
                    Choose a file or drag it here
                  </p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    Supports JPEG, PNG, WebP, and PDF. On mobile, your file
                    picker may also offer camera photo selection.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex items-center justify-center rounded-full bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:bg-blue-300 disabled:text-white"
                >
                  Upload Photo / Document
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3" aria-hidden="true">
          <span className="h-px flex-1 bg-slate-200" />
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
            or
          </span>
          <span className="h-px flex-1 bg-slate-200" />
        </div>

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
          className="inline-flex items-center justify-center rounded-full bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:bg-blue-300 disabled:text-white"
        >
          {isSubmitting ? "Analyzing..." : "Analyze document"}
        </button>
      </div>
    </form>
  );
}
