import PageHeading from "../components/PageHeading.jsx";
import QueueTable from "../components/QueueTable.jsx";
import { useApplications } from "../context/ApplicationsContext.jsx";

export default function ApprovalPage() {
  const { applications, setStatus } = useApplications();
  const rows = applications.filter((a) => a.status === "kyc_passed");
  const decided = applications.filter((a) => a.status === "approved" || a.status === "rejected");

  return (
    <>
      <PageHeading title="Compliance approval" description="Give the final decision on applications that passed KYC review." />
      <div className="card">
        <QueueTable
          rows={rows}
          emptyMessage="No applications are waiting for approval."
          actions={[
            { label: "Approve", variant: "primary", onClick: (r) => setStatus(r.id, "approved") },
            { label: "Reject", variant: "danger", onClick: (r) => setStatus(r.id, "rejected") },
          ]}
        />
      </div>

      <h2 className="section-title">Decided</h2>
      <div className="card">
        <QueueTable rows={decided} emptyMessage="No decisions yet." />
      </div>
    </>
  );
}
