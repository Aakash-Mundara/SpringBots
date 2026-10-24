const TABS = [
  { id: "signin", label: "Sign in" },
  { id: "create", label: "Create account" },
];

export default function AuthTabs({ value, onChange }) {
  return (
    <div className="tabs" role="tablist">
      {TABS.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={value === t.id}
          className={`tabs__tab${value === t.id ? " tabs__tab--active" : ""}`}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
