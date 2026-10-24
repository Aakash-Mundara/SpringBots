import { Link } from "react-router-dom";
import StatusPill from "./StatusPill.jsx";

export default function Header({ ocrEngine = "rapidocr", children }) {
  return (
    <header className="header">
      <Link to="/" className="header__brand">
        <span className="header__name">OnboardIQ</span>
        <span className="header__tagline">Local KYC · AI document reading · Maker-checker</span>
      </Link>
      <div className="header__right">
        {children}
        <StatusPill label={`OCR: ${ocrEngine}`} />
      </div>
    </header>
  );
}
