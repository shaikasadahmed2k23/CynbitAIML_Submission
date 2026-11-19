import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import Header from "./components/Header";
import Review from "./pages/Review";
import Queue from "./pages/Queue";
import How from "./pages/How";

function NotFound() {
  return (
    <div className="card mx-auto max-w-md px-6 py-14 text-center">
      <p className="label">404</p>
      <h1 className="mt-2 text-2xl font-extrabold">Page not found</h1>
      <p className="mt-2 text-sm text-muted">That page doesn't exist.</p>
      <Link to="/" className="btn-primary mt-6">Back to review</Link>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-pill focus:bg-primary focus:px-4 focus:py-2 focus:text-white">Skip to content</a>
      <Header />
      <main id="main" className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
        <Routes>
          <Route path="/" element={<Review />} />
          <Route path="/queue" element={<Queue />} />
          <Route path="/how" element={<How />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="border-t border-line py-8 text-center">
        <p className="hint">BitReview AI · AI/ML Engineer Intern assignment for Cynbit Technologies · AI reviews are a first pass; mentors have the final say.</p>
      </footer>
    </BrowserRouter>
  );
}
