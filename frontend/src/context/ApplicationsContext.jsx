import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { SEED_APPLICATIONS } from "../data/seedApplications.js";

const ApplicationsContext = createContext(null);

export function ApplicationsProvider({ children }) {
  const [applications, setApplications] = useState(SEED_APPLICATIONS);

  const submit = useCallback(({ name, pan }) => {
    const id = `APP-${1000 + (Date.now() % 9000)}`;
    const record = { id, name, pan, status: "submitted", submittedAt: new Date().toISOString().slice(0, 10) };
    setApplications((list) => [record, ...list]);
    return record;
  }, []);

  const setStatus = useCallback((id, status) => {
    setApplications((list) => list.map((a) => (a.id === id ? { ...a, status } : a)));
  }, []);

  const value = useMemo(() => ({ applications, submit, setStatus }), [applications, submit, setStatus]);
  return <ApplicationsContext.Provider value={value}>{children}</ApplicationsContext.Provider>;
}

export function useApplications() {
  const ctx = useContext(ApplicationsContext);
  if (!ctx) throw new Error("useApplications must be used inside <ApplicationsProvider>");
  return ctx;
}
