import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { LoginPage } from "@/features/auth/LoginPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { CollegesPage } from "@/features/colleges/CollegesPage";
import { AdminsPage } from "@/features/users/AdminsPage";
import { StaffPage } from "@/features/users/StaffPage";
import { DepartmentsPage } from "@/features/organization/DepartmentsPage";
import { ClassesPage } from "@/features/organization/ClassesPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/dashboard", element: <DashboardPage /> },

          // super_admin only
          {
            element: <ProtectedRoute allowedRoles={["super_admin"]} />,
            children: [
              { path: "/colleges", element: <CollegesPage /> },
              { path: "/admins", element: <AdminsPage /> },
            ],
          },

          // admin + super_admin
          {
            element: <ProtectedRoute allowedRoles={["super_admin", "admin"]} />,
            children: [
              { path: "/departments", element: <DepartmentsPage /> },
              { path: "/staff", element: <StaffPage /> },
            ],
          },

          // admin + staff (+ super_admin can browse too)
          {
            element: <ProtectedRoute allowedRoles={["super_admin", "admin", "staff"]} />,
            children: [{ path: "/classes", element: <ClassesPage /> }],
          },

          // Batch 3+ routes (topics, problems, exams, quizzes, submissions,
          // student exam-taking flow) get added here the same way.
        ],
      },
    ],
  },
  { path: "/", element: <Navigate to="/dashboard" replace /> },
  { path: "*", element: <Navigate to="/dashboard" replace /> },
]);
