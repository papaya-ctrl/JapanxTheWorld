import { render, screen, within } from "@testing-library/react";
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
      screen.getByText("Please paste document text before starting analysis."),
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
  });

  it("renders Life Guide cards", async () => {
    renderRoute("/life-guides");

    expect(
      await screen.findByRole("heading", {
        name: "Address Registration After Moving",
      }),
    ).toBeInTheDocument();
  });

  it("renders guide detail", async () => {
    renderRoute("/life-guides/moving-address-registration");

    expect(
      await screen.findByRole("heading", {
        name: "Address Registration After Moving",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Required documents")).toBeInTheDocument();
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
      screen.getByText("No clear deadline was found in this result."),
    ).toBeInTheDocument();
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

    expect(screen.getByText("Urgent")).toBeInTheDocument();
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
