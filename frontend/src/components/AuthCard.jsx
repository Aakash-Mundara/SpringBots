import { useState } from "react";
import AuthTabs from "./AuthTabs.jsx";
import TextField from "./TextField.jsx";
import DemoAccounts from "./DemoAccounts.jsx";

export default function AuthCard({ onSignIn, onRegister }) {
  const [mode, setMode] = useState("signin");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const switchMode = (next) => {
    setMode(next);
    setError("");
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const action = mode === "signin" ? onSignIn : onRegister;
    const result = action({ username, password });
    if (!result.ok) setError(result.error);
  };

  const pickDemo = (account) => {
    setMode("signin");
    setUsername(account.username);
    setPassword(account.password);
    setError("");
  };

  return (
    <section className="card auth-card">
      <AuthTabs value={mode} onChange={switchMode} />
      <form onSubmit={handleSubmit} noValidate>
        <TextField label="Username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        <TextField
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete={mode === "signin" ? "current-password" : "new-password"}
          error={error}
        />
        <button type="submit" className="btn btn--primary btn--block">
          {mode === "signin" ? "Sign in" : "Create account"}
        </button>
      </form>
      <DemoAccounts onPick={pickDemo} />
    </section>
  );
}
