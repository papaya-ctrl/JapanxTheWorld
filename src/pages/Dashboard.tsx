import { useEffect, useMemo, useState } from "react";
import {
  createChecklistItem,
  deleteChecklistItem,
  getChecklist,
  updateChecklistItem,
} from "../api/client";
import { ChecklistItem } from "../components/ChecklistItem";
import type {
  ApiError,
  ChecklistCreateInput,
  ChecklistItem as ChecklistItemType,
  UiStatus,
} from "../types";

const initialForm: ChecklistCreateInput = {
  title: "",
  dueDate: "",
  category: "",
};

export function Dashboard() {
  const [status, setStatus] = useState<UiStatus>("loading");
  const [items, setItems] = useState<ChecklistItemType[]>([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [form, setForm] = useState<ChecklistCreateInput>(initialForm);
  const [formMessage, setFormMessage] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    let active = true;

    const loadChecklist = async () => {
      setStatus("loading");

      try {
        const nextItems = await getChecklist();
        if (!active) {
          return;
        }
        setItems(nextItems);
        setStatus(nextItems.length ? "success" : "empty");
      } catch (error) {
        if (!active) {
          return;
        }
        const apiError = error as ApiError;
        setErrorMessage(
          apiError.message || "The checklist could not be loaded right now.",
        );
        setStatus("error");
      }
    };

    void loadChecklist();

    return () => {
      active = false;
    };
  }, []);

  const completion = useMemo(() => {
    const completed = items.filter((item) => item.completed).length;
    return {
      completed,
      total: items.length,
      remaining: items.length - completed,
    };
  }, [items]);

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!form.title.trim() || !form.category.trim()) {
      setFormMessage("Title and category are required.");
      return;
    }

    setFormMessage("");
    setIsCreating(true);

    try {
      const nextItem = await createChecklistItem({
        title: form.title.trim(),
        category: form.category.trim(),
        dueDate: form.dueDate ? form.dueDate : null,
      });
      setItems((current) => [nextItem, ...current]);
      setForm(initialForm);
      setStatus("success");
    } catch (error) {
      const apiError = error as ApiError;
      setFormMessage(apiError.message || "Your task could not be saved.");
    } finally {
      setIsCreating(false);
    }
  };

  const handleToggle = async (item: ChecklistItemType) => {
    const updated = await updateChecklistItem(item.id, {
      completed: !item.completed,
    });
    setItems((current) =>
      current.map((entry) => (entry.id === item.id ? updated : entry)),
    );
  };

  const handleEdit = async (
    item: ChecklistItemType,
    updates: { title: string; category: string; dueDate: string | null },
  ) => {
    const updated = await updateChecklistItem(item.id, updates);
    setItems((current) =>
      current.map((entry) => (entry.id === item.id ? updated : entry)),
    );
  };

  const handleDelete = async (item: ChecklistItemType) => {
    await deleteChecklistItem(item.id);
    const nextItems = items.filter((entry) => entry.id !== item.id);
    setItems(nextItems);
    setStatus(nextItems.length ? "success" : "empty");
  };

  return (
    <div className="space-y-8">
      <section className="grid gap-5 lg:grid-cols-[1fr_1fr_1fr]">
        <article className="rounded-[28px] bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-700">
            Completed
          </p>
          <p className="mt-4 text-4xl font-semibold text-slate-900">
            {completion.completed}
          </p>
        </article>
        <article className="rounded-[28px] bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-700">
            Remaining
          </p>
          <p className="mt-4 text-4xl font-semibold text-slate-900">
            {completion.remaining}
          </p>
        </article>
        <article className="rounded-[28px] bg-gradient-to-br from-red-50 to-white p-6 shadow-sm ring-1 ring-red-100">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-red-700">
            Total tasks
          </p>
          <p className="mt-4 text-4xl font-semibold text-slate-900">
            {completion.total}
          </p>
        </article>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <article className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="space-y-2">
            <h1 className="text-2xl font-semibold text-slate-900">
              Dashboard checklist
            </h1>
            <p className="text-sm leading-6 text-slate-600">
              Keep important tasks visible even before backend accounts and
              authentication are connected.
            </p>
          </div>

          <form onSubmit={handleCreate} className="mt-6 space-y-4">
            <label className="grid gap-2">
              <span className="text-sm font-medium text-slate-800">Task title</span>
              <input
                value={form.title}
                onChange={(event) =>
                  setForm((current) => ({ ...current, title: event.target.value }))
                }
                className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
                placeholder="Example: Visit city office about address change"
              />
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-2">
                <span className="text-sm font-medium text-slate-800">Category</span>
                <input
                  value={form.category}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      category: event.target.value,
                    }))
                  }
                  className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
                  placeholder="City Hall"
                />
              </label>
              <label className="grid gap-2">
                <span className="text-sm font-medium text-slate-800">Due date</span>
                <input
                  type="date"
                  value={form.dueDate ?? ""}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      dueDate: event.target.value,
                    }))
                  }
                  className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
                />
              </label>
            </div>

            {formMessage ? (
              <p className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
                {formMessage}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={isCreating}
              className="inline-flex rounded-full bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:bg-blue-300 disabled:text-white"
            >
              {isCreating ? "Saving..." : "Add checklist item"}
            </button>
          </form>
        </article>

        <section className="space-y-4">
          {status === "loading" ? (
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, index) => (
                <div
                  key={index}
                  className="h-28 animate-pulse rounded-[28px] bg-white shadow-sm ring-1 ring-slate-200"
                />
              ))}
            </div>
          ) : null}

          {status === "error" ? (
            <div className="rounded-[28px] border border-red-100 bg-red-50 px-6 py-5">
              <p className="text-sm font-semibold text-red-700">
                The checklist could not be loaded
              </p>
              <p className="mt-2 text-sm text-red-700/90">{errorMessage}</p>
            </div>
          ) : null}

          {status === "empty" ? (
            <div className="rounded-[28px] border border-slate-200 bg-white px-6 py-8 text-center">
              <p className="text-lg font-semibold text-slate-900">
                Your checklist is empty
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Add your first task to keep deadlines and procedures organized.
              </p>
            </div>
          ) : null}

          {(status === "success" || (status === "empty" && items.length > 0)) ? (
            <div className="space-y-4">
              {items.map((item) => (
                <ChecklistItem
                  key={item.id}
                  item={item}
                  onToggle={handleToggle}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          ) : null}
        </section>
      </section>
    </div>
  );
}
