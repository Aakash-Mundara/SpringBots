import PageHeading from "../components/PageHeading.jsx";
import QueueTable from "../components/QueueTable.jsx";
import { useApplications } from "../context/ApplicationsContext.jsx";

export default function ReviewPage() {
  const { applications, setStatus } = useApplications();
  const rows = applications.filter((a) => a.status === "submitted");

  return (
    <>
      <PageHeading title="KYC review" description="Check each application against its documents, then pass it to a compliance officer." />
      <div className="card">
        <QueueTable
          rows={rows}
          emptyMessage="No applications are waiting for KYC review."
          actions={[
            { label: "Pass to compliance", variant: "primary", onClick: (r) => setStatus(r.id, "kyc_passed") },
            { label: "Reject", variant: "danger", onClick: (r) => setStatus(r.id, "rejected") },
          ]}
        />
      </div>
    </>
  );
}
