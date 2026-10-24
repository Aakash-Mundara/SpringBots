import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import Header from "../components/Header.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { linksFor } from "../data/roles.js";

export default function AppLayout() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  if (!user) return <Navigate to="/login" replace />;

  const handleSignOut = () => {
    signOut();
    navigate("/login", { replace: true });
  };

  return (
    <div className="app">
      <Header>
        <nav className="nav" aria-label="Primary">
          {linksFor(user).map((l) => (
            <NavLink key={l.to} to={l.to} className={({ isActive }) => `nav__link${isActive ? " nav__link--active" : ""}`}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <span className="header__user">{user.label}</span>
        <button type="button" className="btn btn--outline-light btn--sm" onClick={handleSignOut}>Sign out</button>
      </Header>
      <main className="container">
        <Outlet />
      </main>
    </div>
  );
}
