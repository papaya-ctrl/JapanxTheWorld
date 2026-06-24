import { Navigate, Outlet, Route, Routes } from "react-router";
import { Footer } from "./components/Footer";
import { Navbar } from "./components/Navbar";
import { DocumentDecoder } from "./pages/DocumentDecoder";
import { DocumentResult } from "./pages/DocumentResult";
import { Dashboard } from "./pages/Dashboard";
import { GuideDetail } from "./pages/GuideDetail";
import { HelpCenter } from "./pages/HelpCenter";
import { Home } from "./pages/Home";
import { LifeGuides } from "./pages/LifeGuides";
import { StudentWorker } from "./pages/StudentWorker";

const navLinks = [
  { label: "Home", to: "/" },
  { label: "Document Decoder", to: "/document-decoder" },
  { label: "Life Guides", to: "/life-guides" },
  { label: "Student-to-Worker", to: "/student-to-worker" },
  { label: "Dashboard", to: "/dashboard" },
  { label: "Help Center", to: "/help-center" },
];

function AppLayout() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(37,99,235,0.12),_transparent_35%),linear-gradient(180deg,_#f8fbff_0%,_#ffffff_50%,_#f8fafc_100%)] text-slate-900">
      <Navbar links={navLinks} />
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Home />} />
        <Route path="/document-decoder" element={<DocumentDecoder />} />
        <Route path="/document-decoder/result" element={<DocumentResult />} />
        <Route path="/life-guides" element={<LifeGuides />} />
        <Route path="/life-guides/:guideId" element={<GuideDetail />} />
        <Route path="/student-to-worker" element={<StudentWorker />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/help-center" element={<HelpCenter />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
