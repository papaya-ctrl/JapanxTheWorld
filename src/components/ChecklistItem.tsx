import { useState } from "react";
import type { ChecklistItem as ChecklistItemType } from "../types";

type ChecklistItemProps = {
  item: ChecklistItemType;
  onToggle: (item: ChecklistItemType) => Promise<void>;
  onEdit: (
    item: ChecklistItemType,
    updates: { title: string; category: string; dueDate: string | null },
  ) => Promise<void>;
  onDelete: (item: ChecklistItemType) => Promise<void>;
};

export function ChecklistItem({
  item,
  onToggle,
  onEdit,
  onDelete,
}: ChecklistItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState(item.title);
  const [draftCategory, setDraftCategory] = useState(item.category);
  const [draftDueDate, setDraftDueDate] = useState(item.dueDate ?? "");
  const [rowMessage, setRowMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    if (!draftTitle.trim() || !draftCategory.trim()) {
      setRowMessage("Title and category are required.");
      return;
    }

    setIsSaving(true);
    setRowMessage("");

    try {
      await onEdit(item, {
        title: draftTitle.trim(),
        category: draftCategory.trim(),
        dueDate: draftDueDate ? draftDueDate : null,
      });
      setIsEditing(false);
    } catch {
      setRowMessage("This task could not be updated right now.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggle = async () => {
    setIsSaving(true);
    setRowMessage("");

    try {
      await onToggle(item);
    } catch {
      setRowMessage("This task could not be updated right now.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsSaving(true);
    setRowMessage("");

    try {
      await onDelete(item);
    } catch {
      setRowMessage("This task could not be deleted right now.");
      setIsSaving(false);
    }
  };

  return (
    <article className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex gap-4">
          <button
            type="button"
            onClick={handleToggle}
            disabled={isSaving}
            className={[
              "mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border transition",
              item.completed
                ? "border-blue-600 bg-blue-600 text-white"
                : "border-slate-300 bg-white text-transparent hover:border-blue-400",
            ].join(" ")}
            aria-label={item.completed ? "Mark task incomplete" : "Mark task complete"}
          >
            ✓
          </button>

          <div className="space-y-2">
            {isEditing ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <input
                  value={draftTitle}
                  onChange={(event) => setDraftTitle(event.target.value)}
                  className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100 sm:col-span-2"
                />
                <input
                  value={draftCategory}
                  onChange={(event) => setDraftCategory(event.target.value)}
                  className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
                />
                <input
                  type="date"
                  value={draftDueDate}
                  onChange={(event) => setDraftDueDate(event.target.value)}
                  className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
                />
              </div>
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-3">
                  <h3
                    className={[
                      "text-base font-semibold",
                      item.completed ? "text-slate-400 line-through" : "text-slate-900",
                    ].join(" ")}
                  >
                    {item.title}
                  </h3>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">
                    {item.category}
                  </span>
                </div>
                <p className="text-sm text-slate-500">
                  {item.dueDate
                    ? `Due ${new Date(item.dueDate).toLocaleDateString("en-US", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}`
                    : "No due date added yet"}
                </p>
              </>
            )}

            {rowMessage ? (
              <p className="rounded-2xl border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
                {rowMessage}
              </p>
            ) : null}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {isEditing ? (
            <>
              <button
                type="button"
                onClick={handleSave}
                disabled={isSaving}
                className="rounded-full bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:bg-blue-300"
              >
                {isSaving ? "Saving..." : "Save"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsEditing(false);
                  setDraftTitle(item.title);
                  setDraftCategory(item.category);
                  setDraftDueDate(item.dueDate ?? "");
                  setRowMessage("");
                }}
                className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
              >
                Edit
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={isSaving}
                className="rounded-full border border-red-200 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-60"
              >
                Delete
              </button>
            </>
          )}
        </div>
      </div>
    </article>
  );
}
