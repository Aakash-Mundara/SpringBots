import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { DEMO_ACCOUNTS } from "../data/demoAccounts.js";

const AuthContext = createContext(null);
const SESSION_KEY = "onboardiq.session";
const USERS_KEY = "onboardiq.users";

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable: keep working in memory */
  }
}

const stripPassword = ({ password, ...rest }) => rest;

export function AuthProvider({ children }) {
  const [users, setUsers] = useState(() => read(USERS_KEY, DEMO_ACCOUNTS));
  const [user, setUser] = useState(() => read(SESSION_KEY, null));

  const startSession = useCallback((account) => {
    const safe = stripPassword(account);
    setUser(safe);
    write(SESSION_KEY, safe);
    return safe;
  }, []);

  const signIn = useCallback(
    ({ username, password }) => {
      const name = username.trim().toLowerCase();
      const account = users.find((u) => u.username === name && u.password === password);
      if (!account) return { ok: false, error: "Username or password is incorrect." };
      return { ok: true, user: startSession(account) };
    },
    [users, startSession]
  );

  const register = useCallback(
    ({ username, password }) => {
      const name = username.trim().toLowerCase();
      if (name.length < 3) return { ok: false, error: "Username must be at least 3 characters." };
      if (password.length < 8) return { ok: false, error: "Password must be at least 8 characters." };
      if (users.some((u) => u.username === name)) return { ok: false, error: "That username is taken." };
      const account = { label: name, username: name, password, roles: ["applicant"] };
      const next = [...users, account];
      setUsers(next);
      write(USERS_KEY, next);
      return { ok: true, user: startSession(account) };
    },
    [users, startSession]
  );

  const signOut = useCallback(() => {
    setUser(null);
    write(SESSION_KEY, null);
  }, []);

  const value = useMemo(() => ({ user, signIn, register, signOut }), [user, signIn, register, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
