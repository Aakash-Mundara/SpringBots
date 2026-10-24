const POINTS = [
  "Photos, scans and PDFs read locally: nothing leaves this computer",
  "AI pre-fills your form; you confirm every value",
  "KYC officer reviews, a separate compliance officer approves",
];

export default function HeroPanel() {
  return (
    <section className="hero">
      <p className="hero__eyebrow">Synthetic data · Runs on this machine</p>
      <h2 className="hero__title">Open an account by uploading your documents.</h2>
      <p className="hero__lead">
        OnboardIQ reads PAN, Aadhaar and address proofs with on-device OCR and an optional local AI model, then a
        deterministic rules engine and two human officers decide.
      </p>
      <ul className="hero__list">
        {POINTS.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>
    </section>
  );
}
