import { useState } from "react";
import { Link, NavLink } from "react-router";

type NavbarProps = {
  links: { label: string; to: string }[];
};

export function Navbar({ links }: NavbarProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <Link to="/" className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-600 text-sm font-semibold text-white shadow-lg shadow-blue-600/20">
            JxW
          </span>
          <div>
            <p className="text-sm font-semibold text-slate-900">JapanxTheWorld</p>
            <p className="text-xs text-slate-500">
              Practical support for life in Japan
            </p>
          </div>
        </Link>

        <button
          type="button"
          onClick={() => setIsOpen((open) => !open)}
          className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 sm:hidden"
          aria-expanded={isOpen}
          aria-label="Toggle navigation menu"
        >
          Menu
        </button>

        <nav className="hidden items-center gap-2 sm:flex" aria-label="Primary">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                [
                  "rounded-full px-4 py-2 text-sm font-medium transition",
                  isActive
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                ].join(" ")
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>

      {isOpen ? (
        <nav className="border-t border-slate-200 bg-white px-4 py-3 sm:hidden" aria-label="Mobile">
          <div className="flex flex-col gap-2">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                onClick={() => setIsOpen(false)}
                className={({ isActive }) =>
                  [
                    "rounded-2xl px-4 py-3 text-sm font-medium transition",
                    isActive
                      ? "bg-blue-600 text-white"
                      : "bg-slate-50 text-slate-700 hover:bg-slate-100",
                  ].join(" ")
                }
              >
                {link.label}
              </NavLink>
            ))}
          </div>
        </nav>
      ) : null}
    </header>
  );
}
