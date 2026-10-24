export const ROLE_LINKS = [
  { role: "applicant", to: "/apply", label: "Open an account" },
  { role: "kyc", to: "/review", label: "KYC review" },
  { role: "compliance", to: "/approve", label: "Compliance approval" },
];

export const hasRole = (user, role) => Boolean(user?.roles?.includes(role));

export function linksFor(user) {
  return ROLE_LINKS.filter((l) => hasRole(user, l.role));
}

export function homePathFor(user) {
  return linksFor(user)[0]?.to ?? "/login";
}
