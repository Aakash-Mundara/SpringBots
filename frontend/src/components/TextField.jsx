import { useId } from "react";

export default function TextField({ label, error, ...inputProps }) {
  const id = useId();
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>{label}</label>
      <input id={id} className="field__input" aria-invalid={Boolean(error)} {...inputProps} />
      {error && <p className="field__error">{error}</p>}
    </div>
  );
}
