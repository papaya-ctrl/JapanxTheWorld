import { type ChangeEvent, type DragEvent, type FormEvent, useEffect, useRef, useState } from "react";
import type { DocumentFileInput, DocumentInputFormValues } from "../types";
import { isMockApiEnabled } from "../api/client";

type Props = {
  onSubmit: (values: DocumentInputFormValues) => Promise<void> | void;
  onFileChange?: () => void;
  isSubmitting: boolean;
  errorMessage?: string;
  retryAfterSeconds?: number;
};
const accepted = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
const maxBytes = 10 * 1024 * 1024;
const button = "rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-60";

export function DocumentInputForm({ onSubmit, onFileChange, isSubmitting, errorMessage, retryAfterSeconds = 0 }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const submitting = useRef(false);
  const [selectedFile, setSelectedFile] = useState<DocumentFileInput>();
  const [validationError, setValidationError] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");

  useEffect(() => {
    if (selectedFile?.type.startsWith("image/") && typeof URL.createObjectURL === "function") {
      const url = URL.createObjectURL(selectedFile.file);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    }
    setPreviewUrl("");
  }, [selectedFile]);

  const clearFile = () => {
    setSelectedFile(undefined);
    setValidationError("");
    if (input.current) input.current.value = "";
    onFileChange?.();
  };
  const selectFile = (file?: File) => {
    if (!file || isSubmitting) return;
    const knownMime = accepted.includes(file.type);
    const absentMime = (!file.type || file.type === "application/octet-stream") && /\.(jpe?g|png|webp|pdf)$/i.test(file.name);
    let problem = "";
    if (!knownMime && !absentMime) problem = "Please upload a JPEG, PNG, WebP, or PDF file.";
    else if (!file.size) problem = "This file is empty. Please choose another file.";
    else if (file.size > maxBytes) problem = "Please choose a file smaller than 10 MB.";
    if (problem) {
      clearFile();
      setValidationError(problem);
      return;
    }
    setSelectedFile({ file, name: file.name, type: file.type, size: file.size });
    setValidationError("");
    onFileChange?.();
  };
  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => selectFile(event.target.files?.[0]);
  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    if (isSubmitting) return;
    if (event.dataTransfer.files.length !== 1) {
      setValidationError("Please select one document at a time.");
      return;
    }
    selectFile(event.dataTransfer.files[0]);
  };
  const submit = async () => {
    if (isSubmitting || submitting.current || retryAfterSeconds > 0) return;
    if (!selectedFile) {
      setValidationError("Please choose a supported document file.");
      return;
    }
    setValidationError("");
    submitting.current = true;
    try { await onSubmit({ documentFile: selectedFile }); }
    finally { submitting.current = false; }
  };
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); void submit(); };

  return (
    <form onSubmit={handleSubmit} aria-busy={isSubmitting} className="space-y-6 rounded-[32px] border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60 sm:p-8">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Start document analysis</h2>
        <p className="mt-1 text-sm text-slate-600">Upload a Japanese document image or PDF.</p>
      </div>
      {isMockApiEnabled() ? <p role="note" className="rounded-2xl bg-amber-50 p-4 text-sm text-amber-900">Demo mode: uploaded files are not read. Results are sample explanations.</p> : null}
      <fieldset disabled={isSubmitting} className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <label htmlFor="documentFile" className="text-sm font-medium text-slate-800">Upload Photo / Document</label>
          <span className="text-xs text-slate-500">Max 10 MB · PDF up to 5 pages</span>
        </div>
        <p id="document-file-help" className="text-sm text-slate-600">Supports JPEG, PNG, WebP, and PDF.</p>
        <div onDragEnter={e => { e.preventDefault(); if (!isSubmitting) setIsDragging(true); }}
          onDragOver={e => e.preventDefault()} onDragLeave={() => setIsDragging(false)} onDrop={handleDrop}
          className={`rounded-[28px] border border-dashed p-4 transition sm:p-5 ${isDragging ? "border-blue-400 bg-blue-50" : "border-slate-300 bg-slate-50"}`}>
          <input ref={input} id="documentFile" type="file" accept={`${accepted.join(",")},.jpg,.jpeg,.png,.webp,.pdf`}
            aria-label="Upload Photo / Document" aria-describedby="document-file-help" onChange={handleFileChange} className="sr-only" />
          {selectedFile ? (
            <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
              <div className="flex min-w-0 gap-4">
                {previewUrl ? <img src={previewUrl} alt="Selected document preview" className="h-24 w-24 rounded-2xl border border-slate-200 object-cover" />
                  : <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-2xl border border-red-100 bg-red-50 text-sm font-semibold text-red-700">{selectedFile.type.startsWith("image/") ? "IMG" : selectedFile.type === "application/pdf" ? "PDF" : "FILE"}</div>}
                <div className="min-w-0 space-y-2">
                  <p className="break-words text-sm font-semibold text-slate-900">{selectedFile.name}</p>
                  <p className="text-sm text-slate-600">{selectedFile.type || "Document"} · {(selectedFile.size / 1024 / 1024).toFixed(1)} MB</p>
                  <p className="text-xs text-blue-700">File selected. Ready to analyze.</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => input.current?.click()} className={button}>Replace</button>
                <button type="button" onClick={clearFile} className={button}>Remove file</button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div><p className="text-sm font-semibold text-slate-900">Choose a file or drag it here</p>
                <p className="mt-1 text-sm leading-6 text-slate-600">Choose a clear, complete document.</p></div>
              <button type="button" onClick={() => input.current?.click()} className={button}>Upload Photo / Document</button>
            </div>
          )}
        </div>
      </fieldset>
      {validationError ? <p role="alert" className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{validationError}</p> : null}
      {errorMessage ? <div role="alert" className="space-y-3 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
        <p>{errorMessage}</p>
        <button type="button" onClick={() => void submit()} disabled={isSubmitting || !selectedFile || retryAfterSeconds > 0} className={button}>Retry analysis</button>
      </div> : null}
      <p role="status" aria-live="polite" className="min-h-6 text-sm font-medium text-blue-700">
        {isSubmitting ? "Uploading and analyzing document… This may take up to two minutes." : retryAfterSeconds > 0 ? `Please wait ${retryAfterSeconds} seconds before submitting again.` : ""}
      </p>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs leading-5 text-slate-500">Review uncertain fields against the original document before acting.</p>
        <button type="submit" disabled={isSubmitting || retryAfterSeconds > 0} className="inline-flex items-center justify-center rounded-full bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:bg-blue-300">
          {isSubmitting ? "Analyzing…" : "Analyze document"}
        </button>
      </div>
    </form>
  );
}
