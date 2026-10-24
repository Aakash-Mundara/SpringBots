const LABELS = {
  submitted: "Awaiting KYC",
  kyc_passed: "Awaiting compliance",
  approved: "Approved",
  rejected: "Rejected",
};

export default function StatusBadge({ status }) {
  return <span className={`badge badge--${status}`}>{LABELS[status] ?? status}</span>;
}
