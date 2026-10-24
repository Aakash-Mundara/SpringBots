import { useState } from "react";
import PageHeading from "../components/PageHeading.jsx";
import TextField from "../components/TextField.jsx";
import DocumentSlot from "../components/DocumentSlot.jsx";
import { useApplications } from "../context/ApplicationsContext.jsx";

const SLOTS = [
  { key: "pan", title: "PAN card", hint: "Photo, scan or PDF" },
  { key: "aadhaar", title: "Aadhaar", hint: "Photo, scan or PDF" },
  { key: "address", title: "Address proof", hint: "Utility bill, bank statement or rent agreement" },
];

export default function ApplyPage() {
  const { submit } = useApplications();
  const [name, setName] = useState("");
  const [pan, setPan] = useState("");
  const [files, setFiles] = useState({});
  const [submitted, setSubmitted] = useState(null);

  const ready = name.trim() && pan.trim() && SLOTS.every((s) => files[s.key]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!ready) return;
    setSubmitted(submit({ name: name.trim(), pan: pan.trim().toUpperCase() }));
    setName("");
    setPan("");
    setFiles({});
  };

  return (
    <>
      <PageHeading
        title="Open an account"
        description="Upload your documents. They are read on this computer, and you confirm every value before submitting."
      />

      {submitted && (
        <div className="notice" role="status">
          Application <strong>{submitted.id}</strong> submitted. A KYC officer will review it next.
        </div>
      )}

      <form className="card form-card" onSubmit={handleSubmit}>
        <h2 className="card__title">Documents</h2>
        <div className="slots">
          {SLOTS.map((s) => (
            <DocumentSlot
              key={s.key}
              title={s.title}
              hint={s.hint}
              file={files[s.key]}
              onChange={(f) => setFiles((prev) => ({ ...prev, [s.key]: f }))}
            />
          ))}
        </div>

        <h2 className="card__title">Details</h2>
        <div className="form-row">
          <TextField label="Full name" value={name} onChange={(e) => setName(e.target.value)} />
          <TextField label="PAN" value={pan} maxLength={10} onChange={(e) => setPan(e.target.value)} />
        </div>

        <button type="submit" className="btn btn--primary" disabled={!ready}>Submit application</button>
      </form>
    </>
  );
}
