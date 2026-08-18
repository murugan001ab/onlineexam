import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { FullScreenLoader } from "@/components/ui/Spinner";
import type { RoleName } from "@/types/auth";

interface ProtectedRouteProps {
  allowedRoles?: RoleName[];
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { user, status } = useAuthStore();

  if (status === "idle" || status === "authenticating") {
    return <FullScreenLoader label="Checking your session..." />;
  }

  if (status === "unauthenticated" || !user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
