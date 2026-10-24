import StatusBadge from "./StatusBadge.jsx";

export default function QueueTable({ rows, actions = [], emptyMessage }) {
  if (rows.length === 0) return <p className="empty">{emptyMessage}</p>;

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Reference</th>
            <th>Applicant</th>
            <th>PAN</th>
            <th>Submitted</th>
            <th>Status</th>
            {actions.length > 0 && <th aria-label="Actions" />}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.id}</td>
              <td>{row.name}</td>
              <td className="table__mono">{row.pan}</td>
              <td>{row.submittedAt}</td>
              <td><StatusBadge status={row.status} /></td>
              {actions.length > 0 && (
                <td className="table__actions">
                  {actions.map((a) => (
                    <button key={a.label} type="button" className={`btn btn--sm btn--${a.variant ?? "ghost"}`} onClick={() => a.onClick(row)}>
                      {a.label}
                    </button>
                  ))}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
