import { DEMO_ACCOUNTS, DEMO_PASSWORD } from "../data/demoAccounts.js";

export default function DemoAccounts({ onPick }) {
  return (
    <div className="demo">
      <p className="demo__text">
        Demo accounts (password <strong>{DEMO_PASSWORD}</strong>):
      </p>
      <div className="demo__chips">
        {DEMO_ACCOUNTS.map((a) => (
          <button key={a.username} type="button" className="chip" onClick={() => onPick(a)}>
            {a.label}
          </button>
        ))}
      </div>
    </div>
  );
}
