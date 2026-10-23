import "@testing-library/jest-dom/vitest";

// jsdom has no layout viewport; result-route scrolling is checked in-browser.
window.scrollTo = () => {};
