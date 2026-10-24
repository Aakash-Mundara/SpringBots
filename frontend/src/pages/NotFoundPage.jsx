import { Link } from "react-router-dom";
import Header from "../components/Header.jsx";

export default function NotFoundPage() {
  return (
    <div className="app">
      <Header />
      <main className="container">
        <div className="card not-found">
          <h1>Page not found</h1>
          <p>That address doesn’t exist in OnboardIQ.</p>
          <Link to="/" className="btn btn--primary">Go to home</Link>
        </div>
      </main>
    </div>
  );
}
