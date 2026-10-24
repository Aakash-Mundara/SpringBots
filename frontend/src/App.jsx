import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/LoginPage.jsx";
import ApplyPage from "./pages/ApplyPage.jsx";
import ReviewPage from "./pages/ReviewPage.jsx";
import ApprovalPage from "./pages/ApprovalPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import AppLayout from "./layouts/AppLayout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import { useAuth } from "./context/AuthContext.jsx";
import { homePathFor } from "./data/roles.js";

function RootRedirect() {
  const { user } = useAuth();
  return <Navigate to={user ? homePathFor(user) : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<LoginPage />} />

      <Route element={<AppLayout />}>
        <Route path="/apply" element={<ProtectedRoute role="applicant"><ApplyPage /></ProtectedRoute>} />
        <Route path="/review" element={<ProtectedRoute role="kyc"><ReviewPage /></ProtectedRoute>} />
        <Route path="/approve" element={<ProtectedRoute role="compliance"><ApprovalPage /></ProtectedRoute>} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
