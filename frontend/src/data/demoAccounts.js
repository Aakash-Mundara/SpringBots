export const DEMO_PASSWORD = "Passw0rd!";

export const DEMO_ACCOUNTS = [
  { label: "Applicant", username: "applicant", password: DEMO_PASSWORD, roles: ["applicant"] },
  { label: "KYC officer", username: "kyc_officer", password: DEMO_PASSWORD, roles: ["kyc"] },
  { label: "Compliance officer", username: "compliance_officer", password: DEMO_PASSWORD, roles: ["compliance"] },
  { label: "KYC + Compliance", username: "kyc_compliance", password: DEMO_PASSWORD, roles: ["kyc", "compliance"] },
];
