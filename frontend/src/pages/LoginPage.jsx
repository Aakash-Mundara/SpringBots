import { Navigate, useLocation, useNavigate } from "react-router-dom";
import Header from "../components/Header.jsx";
import HeroPanel from "../components/HeroPanel.jsx";
import AuthCard from "../components/AuthCard.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { homePathFor } from "../data/roles.js";

export default function LoginPage() {
  const { user, signIn, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  if (user) return <Navigate to={homePathFor(user)} replace />;

  const finish = (result) => {
    if (result.ok) navigate(location.state?.from ?? homePathFor(result.user), { replace: true });
    return result;
  };

  return (
    <div className="app">
      <Header />
      <main className="container login-grid">
        <HeroPanel />
        <AuthCard onSignIn={(c) => finish(signIn(c))} onRegister={(c) => finish(register(c))} />
      </main>
    </div>
  );
}
