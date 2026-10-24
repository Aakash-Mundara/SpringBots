import { useId } from "react";

export default function DocumentSlot({ title, hint, file, onChange }) {
  const id = useId();
  return (
    <div className={`slot${file ? " slot--filled" : ""}`}>
      <div>
        <p className="slot__title">{title}</p>
        <p className="slot__hint">{file ? file.name : hint}</p>
      </div>
      <label htmlFor={id} className="btn btn--ghost btn--sm">
        {file ? "Replace" : "Choose file"}
      </label>
      <input
        id={id}
        className="visually-hidden"
        type="file"
        accept="image/*,.pdf"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
    </div>
  );
}
