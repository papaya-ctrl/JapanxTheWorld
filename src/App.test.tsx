import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, beforeEach } from "vitest";
import App from "./App";
import { analyzeDocument } from "./api/client";

const renderRoute = (route = "/") =>
  render(
    <MemoryRouter initialEntries={[route]}>
      <App />
    </MemoryRouter>,
  );

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("JapanxTheWorld app", () => {
  it("renders the home page", () => {
    renderRoute("/");

    expect(
      screen.getByRole("heading", {
        name: "A calmer way to understand life and documents in Japan",
      }),
    ).toBeInTheDocument();
  });

  it("renders the document decoder page", () => {
    renderRoute("/document-decoder");

    expect(
      screen.getByRole("heading", {
        name: "Understand a Japanese document step by step",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Privacy warning")).toBeInTheDocument();
  });

  it("prevents empty document submission", async () => {
    const user = userEvent.setup();
    renderRoute("/document-decoder");

    await user.click(screen.getByRole("button", { name: "Analyze document" }));

    expect(
      screen.getByText("Please paste document text or choose a supported document file."),
    ).toBeInTheDocument();
  });

  it("shows loading and navigates to a mock template result", async () => {
    const user = userEvent.setup();
    renderRoute("/document-decoder");

    await user.click(screen.getByRole("button", { name: "Try sample text" }));
    await user.click(screen.getByRole("button", { name: "Analyze document" }));

    expect(screen.getByText("Analyzing document...")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "Residence Tax Notice" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Verified Guide")).toBeInTheDocument();
    expect(
      screen.getByText("Based on JapanxTheWorld trusted content"),
    ).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Important Points" })).toBeInTheDocument();
  });

  it("renders Life Guide cards", async () => {
    renderRoute("/life-guides");

    expect(
      await screen.findByRole("heading", {
        name: "Address Registration / Moving",
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "National Pension" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Part-Time Work Permission" })).toBeInTheDocument();
  });

  it("renders guide detail", async () => {
    renderRoute("/life-guides/moving-address-registration");

    expect(
      await screen.findByRole("heading", {
        name: "Address Registration / Moving",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("住所変更・転入・転出")).toBeInTheDocument();
    expect(screen.getByText("What this is")).toBeInTheDocument();
    expect(screen.getByText("Why this matters / why you may receive it")).toBeInTheDocument();
    expect(screen.getByText("Required documents")).toBeInTheDocument();
    expect(screen.getByText("Common mistakes")).toBeInTheDocument();
    expect(screen.getByText("Example situation")).toBeInTheDocument();
    expect(screen.getByText("Official confirmation / source section")).toBeInTheDocument();
    expect(screen.getByText("Official confirmation needed")).toBeInTheDocument();
    expect(screen.getByRole("note", { name: "Important rule" })).toBeInTheDocument();
    expect(screen.getByRole("note", { name: "Time-sensitive" })).toBeInTheDocument();
    expect(screen.getByRole("note", { name: "Recommended next action" })).toBeInTheDocument();
    expect(screen.getByRole("note", { name: "Official confirmation" })).toBeInTheDocument();
    expect(screen.getByText("Start here")).toBeInTheDocument();
  });

  it("renders dashboard checklist and can toggle an item", async () => {
    const user = userEvent.setup();
    renderRoute("/dashboard");

    const task = await screen.findByText("Pay health insurance notice");
    expect(task).toBeInTheDocument();
    const taskCard = task.closest("article");
    expect(taskCard).not.toBeNull();

    await user.click(
      within(taskCard as HTMLElement).getByRole("button", {
        name: "Mark task complete",
      }),
    );

    expect(
      await within(taskCard as HTMLElement).findByRole("button", {
        name: "Mark task incomplete",
      }),
    ).toBeInTheDocument();
  });

  it("renders Help Center resources", async () => {
    renderRoute("/help-center");

    expect(
      await screen.findByText("Immigration Services Agency of Japan"),
    ).toBeInTheDocument();
  });

  it("renders Student-to-Worker official resources through the API layer", async () => {
    renderRoute("/student-to-worker");

    expect(
      await screen.findByText("Immigration Services Agency of Japan"),
    ).toBeInTheDocument();
    expect(await screen.findByText("Hello Work")).toBeInTheDocument();
  });

  it("opens the mobile navigation menu", async () => {
    const user = userEvent.setup();
    renderRoute("/");

    const menuButton = screen.getByRole("button", { name: "Toggle navigation menu" });
    await user.click(menuButton);

    expect(menuButton).toHaveAttribute("aria-expanded", "true");
    expect(screen.getAllByRole("link", { name: "Dashboard" }).length).toBeGreaterThan(0);
  });

  it("uses explicit readable text color on primary feature buttons", () => {
    renderRoute("/");

    expect(screen.getByRole("link", { name: "Open decoder" })).toHaveClass(
      "text-white",
      "hover:text-white",
      "hover:bg-blue-700",
      "focus-visible:ring-2",
      "focus-visible:ring-blue-500",
    );
  });
});

describe("Document decoder upload flow", () => {
  it("supports text-only document submission", async () => {
    const user = userEvent.setup();
    renderRoute("/document-decoder");

    await user.type(
      screen.getByRole("textbox", { name: "Document text" }),
      "国民健康保険料のお知らせです。2026年8月10日までにお支払いください。",
    );
    await user.click(screen.getByRole("button", { name: "Analyze document" }));

    expect(
      await screen.findByRole("heading", {
        name: "National Health Insurance Notice",
      }),
    ).toBeInTheDocument();
  });

  it("shows selected image file details", async () => {
    const user = userEvent.setup();
    renderRoute("/document-decoder");

    const imageFile = new File(["synthetic image"], "health-insurance.webp", {
      type: "image/webp",
    });
    await user.upload(
      screen.getByLabelText("Upload Photo / Document"),
      imageFile,
    );

    expect(screen.getByText("health-insurance.webp")).toBeInTheDocument();
    expect(screen.getByText(/image\/webp/)).toBeInTheDocument();
    expect(screen.getByAltText("Selected document preview")).toBeInTheDocument();
  });

  it("shows selected PDF file details", async () => {
    const user = userEvent.setup();
    renderRoute("/document-decoder");

    const pdfFile = new File(["synthetic pdf"], "residence-tax.pdf", {
      type: "application/pdf",
    });
    await user.upload(
      screen.getByLabelText("Upload Photo / Document"),
      pdfFile,
    );

    expect(screen.getByText("residence-tax.pdf")).toBeInTheDocument();
    expect(screen.getByText(/application\/pdf/)).toBeInTheDocument();
    expect(screen.getByText("PDF")).toBeInTheDocument();
  });

  it("rejects unsupported file types", async () => {
    renderRoute("/document-decoder");

    const textFile = new File(["not supported"], "memo.txt", {
      type: "text/plain",
    });
    fireEvent.change(
      screen.getByLabelText("Upload Photo / Document"),
      {
        target: {
          files: [textFile],
        },
      },
    );

    expect(
      screen.getByText("Please upload a JPEG, PNG, WebP, or PDF file."),
    ).toBeInTheDocument();
  });

  it("rejects oversized files", async () => {
    const user = userEvent.setup();
    renderRoute("/document-decoder");

    const largePdf = new File(
      [new Uint8Array(10 * 1024 * 1024 + 1)],
      "large-document.pdf",
      { type: "application/pdf" },
    );
    await user.upload(
      screen.getByLabelText("Upload Photo / Document"),
      largePdf,
    );

    expect(
      screen.getByText("Please choose a file smaller than 10 MB."),
    ).toBeInTheDocument();
  });

  it("removes a selected file", async () => {
    const user = userEvent.setup();
    renderRoute("/document-decoder");

    const pdfFile = new File(["synthetic pdf"], "remove-me.pdf", {
      type: "application/pdf",
    });
    await user.upload(
      screen.getByLabelText("Upload Photo / Document"),
      pdfFile,
    );
    await user.click(screen.getByRole("button", { name: "Remove file" }));

    expect(screen.queryByText("remove-me.pdf")).not.toBeInTheDocument();
    expect(screen.getByText("Choose a file or drag it here")).toBeInTheDocument();
  });

  it("allows valid file-only mock analysis", async () => {
    const user = userEvent.setup();
    renderRoute("/document-decoder");

    const pdfFile = new File(["synthetic pdf"], "residence-tax.pdf", {
      type: "application/pdf",
    });
    await user.upload(
      screen.getByLabelText("Upload Photo / Document"),
      pdfFile,
    );

    const analyzeButton = screen.getByRole("button", { name: "Analyze document" });
    expect(analyzeButton).toBeEnabled();
    await user.click(analyzeButton);

    expect(screen.getByText("Analyzing document...")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "Residence Tax Notice" }),
    ).toBeInTheDocument();
    expect(screen.getByText("No clear deadline detected")).toBeInTheDocument();
    expect(screen.getByText(/not read with OCR/)).toBeInTheDocument();
  });
});

describe("Document result rendering", () => {
  it("shows an empty-result recovery state", () => {
    renderRoute("/document-decoder/result");

    expect(
      screen.getByRole("heading", { name: "Start with a document first" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open Document Decoder" }),
    ).toBeInTheDocument();
  });

  it("renders an AI fallback result", () => {
    window.sessionStorage.setItem(
      "japanxtheworld.lastAnalysis",
      JSON.stringify({
        source: "ai",
        documentType: "Unknown Official Document",
        summary: "This document is unclear from the provided text.",
        deadline: null,
        urgency: "important",
        importantPoints: ["The exact purpose is unclear."],
        nextSteps: ["Confirm with the issuing organization."],
        relatedGuide: null,
        officialWarning:
          "Please confirm important details with official sources.",
      }),
    );

    renderRoute("/document-decoder/result");

    expect(screen.getByText("AI-assisted Explanation")).toBeInTheDocument();
    expect(
      screen.getByText("No clear deadline detected"),
    ).toBeInTheDocument();
    expect(screen.getByRole("note", { name: "Official confirmation warning" })).toBeInTheDocument();
  });

  it("renders urgency badges correctly", () => {
    window.sessionStorage.setItem(
      "japanxtheworld.lastAnalysis",
      JSON.stringify({
        source: "template",
        documentType: "Test Notice",
        summary: "A test summary.",
        deadline: "2026-12-01",
        urgency: "urgent",
        importantPoints: ["Point"],
        nextSteps: ["Step"],
        relatedGuide: null,
        officialWarning: "Confirm with official sources.",
      }),
    );

    renderRoute("/document-decoder/result");

    expect(screen.getByText("Status: Urgent")).toBeInTheDocument();
  });
});

describe("Document decoder error state", () => {
  it("provides a retry action after a recoverable error", async () => {
    const user = userEvent.setup();
    renderRoute("/document-decoder");

    await user.type(
      screen.getByRole("textbox", { name: "Document text" }),
      "simulate:server-error 市役所からの通知です。",
    );
    await user.click(screen.getByRole("button", { name: "Analyze document" }));

    const alert = await screen.findByRole("alert");
    expect(
      within(alert).getByText("Something went wrong while analyzing this document."),
    ).toBeInTheDocument();
    expect(
      within(alert).getByRole("button", { name: "Retry analysis" }),
    ).toBeInTheDocument();
  });
});

describe("mock analysis simulations", () => {
  it("can simulate a timeout", async () => {
    await expect(
      analyzeDocument({
        documentText: "simulate:timeout 市役所からの通知です。",
      }),
    ).rejects.toMatchObject({
      code: "ANALYSIS_TIMEOUT",
    });
  });

  it("can simulate a malformed analysis result", async () => {
    await expect(
      analyzeDocument({
        documentText: "simulate:malformed 市役所からの通知です。",
      }),
    ).rejects.toMatchObject({
      code: "MALFORMED_ANALYSIS",
    });
  });

  it("can simulate a no-deadline result", async () => {
    await expect(
      analyzeDocument({
        documentText: "simulate:no-deadline 市役所からのお知らせです。",
      }),
    ).resolves.toMatchObject({
      deadline: null,
      documentType: "Unknown Official Document",
    });
  });
});
