import type { ChecklistItem } from "../types";

export const mockChecklist: ChecklistItem[] = [
  {
    id: "task-1",
    title: "Pay health insurance notice",
    completed: false,
    dueDate: "2026-08-10",
    category: "Insurance",
  },
  {
    id: "task-2",
    title: "Confirm address registration after moving",
    completed: true,
    dueDate: "2026-07-05",
    category: "City Hall",
  },
  {
    id: "task-3",
    title: "Check job hunting deadlines before graduation",
    completed: false,
    dueDate: null,
    category: "Career",
  },
];
