import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { AnalysisResultCard } from "./AnalysisResultCard";
import { uploadResult, field } from "../test/documentFixtures";
import { formatDocumentDate, formatDocumentDatesInText, isISODate } from "../lib/documentDates";

const show = (result = uploadResult()) => render(<MemoryRouter><AnalysisResultCard result={result} /></MemoryRouter>);

describe("evidence-based result presentation", () => {
  it("shows partial status and the actual deterministic source", () => {
    show();
    expect(screen.getByRole("status", { name: "Extraction status" })).toHaveAttribute("data-extraction-status", "partial");
    expect(screen.getByText("Partial extraction")).toBeInTheDocument();
    expect(screen.getByText("Local document analysis")).toBeInTheDocument();
    expect(screen.queryByText("AI-assisted Explanation")).not.toBeInTheDocument();
    expect(screen.queryByText("Analysis complete")).not.toBeInTheDocument();
    expect(screen.queryByText(/Status: Urgent|Low urgency/)).not.toBeInTheDocument();
  });
  it("keeps payment and usage expiration dates in separately labeled cards", () => {
    show();
    const payment = screen.getByRole("heading", { name: "Payment deadline" }).closest("li")!;
    const usage = screen.getByRole("heading", { name: "Usage expiration date" }).closest("li")!;
    expect(within(payment).getByText("November 2, 2026")).toBeInTheDocument();
    expect(within(usage).getByText("November 2, 2027")).toBeInTheDocument();
    const primary = screen.getByRole("heading", { name: "Primary deadline" }).parentElement!;
    expect(within(primary).getByText("November 2, 2026")).toBeInTheDocument();
    expect(within(primary).queryByText("November 2, 2027")).not.toBeInTheDocument();
  });
  it("shows a verified amount even with a null primary amount, without summing repeats", () => {
    show();
    const payment = screen.getByRole("heading", { name: "Payment amount" }).closest("li")!;
    expect(within(payment).getByText("JPY 18,000")).toBeInTheDocument();
    expect(within(payment).getByText("Verified field")).toBeInTheDocument();
    expect(within(payment).getByText("Repeated in 3 sections; shown once.")).toBeInTheDocument();
    const primary = screen.getByRole("heading", { name: "Primary amount" }).parentElement!;
    expect(primary).toHaveTextContent("not been conclusively selected");
    expect(primary).not.toHaveTextContent("18,000");
    expect(screen.queryByText("JPY 54,000")).not.toBeInTheDocument();
  });
  it("shows only relevant original Japanese snippets on inspection, with page numbers", async () => {
    const user = userEvent.setup(); show();
    const payment = screen.getByRole("heading", { name: "Payment deadline" }).closest("li")!;
    await user.click(within(payment).getByText("View original source text"));
    expect(within(payment).getByText("納期限 令和8年11月2日")).toBeVisible();
    expect(within(payment).getByText("Page 1")).toBeVisible();
    expect(screen.queryByText(/UNRELATED_PRIVATE_ADDRESS/)).not.toBeInTheDocument();
    expect(screen.queryByText("p1-b1")).not.toBeInTheDocument();
  });
  it("does not invent missing document facts or a summary", () => {
    show(uploadResult({ documentType: null, summary: null, primaryAmount: null, primaryDeadline: null, deadline: null,
      deadlines: [], amounts: [], importantPoints: [], nextSteps: [], evidence: [], documentTypeEvidenceIds: [], warnings: [], extractionStatus: "no_fields" }));
    expect(screen.getByRole("heading", { name: "Unknown Document" })).toBeInTheDocument();
    expect(screen.getByText("No verified summary is available.")).toBeInTheDocument();
    expect(screen.getByText("No deadline was extracted.")).toBeInTheDocument();
    expect(screen.getByText("No amount was extracted.")).toBeInTheDocument();
    expect(screen.getByText("No supported fields found")).toBeInTheDocument();
    expect(screen.queryByText(/November|JPY/)).not.toBeInTheDocument();
  });
  it("distinguishes an unverified candidate from a missing value", () => {
    show(uploadResult({ extractionStatus: "unverified", primaryDeadline: null, deadline: null,
      deadlines: [{ ...field("Application deadline", "application", "p1-b1"), status: "unverified", reasons: ["Low confidence."], date: "2026-11-02" },
        { ...field("Submission deadline", "submission", "p1-b2"), status: "unverified", reasons: ["Incomplete date."], date: null }] }));
    expect(screen.getByText("Candidate date:", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Date unverified")).toBeInTheDocument();
    expect(screen.getByText("Unverified extraction")).toBeInTheDocument();
    expect(screen.getAllByText("Unverified field").length).toBeGreaterThan(1);
  });
  it("shows the selected primary amount including a valid zero", () => {
    show(uploadResult({ primaryAmount: 0, amounts: [{ ...field("Unpaid amount", "outstanding", "p1-b3"), value: 0, currency: "JPY" }] }));
    const primary = screen.getByRole("heading", { name: "Primary amount" }).parentElement!;
    expect(within(primary).getByText("JPY 0")).toBeInTheDocument();
  });
  it("uses the real verified status without declaring document authenticity", () => {
    show(uploadResult({ extractionStatus: "verified" }));
    expect(screen.getByText("Analysis complete")).toBeInTheDocument();
    expect(screen.getByText(/Document authenticity is not assessed/)).toBeInTheDocument();
  });
});

describe("English date-only formatting", () => {
  it("does not construct timezone-dependent dates", () => {
    expect(formatDocumentDate("2026-11-02")).toBe("November 2, 2026");
    expect(formatDocumentDate("2026-01-01")).toBe("January 1, 2026");
    expect(formatDocumentDate("2024-02-29")).toBe("February 29, 2024");
    expect(formatDocumentDatesInText("Deadline: 2026-11-02.")).toBe("Deadline: November 2, 2026.");
  });
  it.each(["2026-02-29", "2026-13-01", "2026-02-30", "0000-01-01", "2026-1-2", "unknown"])("never repairs an invalid date: %s", value => {
    expect(isISODate(value)).toBe(false);
    expect(formatDocumentDate(value)).toBe("Date unverified");
  });
});
