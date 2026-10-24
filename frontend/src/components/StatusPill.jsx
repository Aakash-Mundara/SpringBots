export default function StatusPill({ label, tone = "ok" }) {
  return (
    <div className="status-pill">
      <span className={`status-pill__dot status-pill__dot--${tone}`} />
      {label}
    </div>
  );
}
