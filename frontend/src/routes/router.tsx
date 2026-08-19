import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { LoginPage } from "@/features/auth/LoginPage";
import { SignupPage } from "@/features/auth/SignupPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { CollegesPage } from "@/features/colleges/CollegesPage";
import { AdminsPage } from "@/features/users/AdminsPage";
import { StaffPage } from "@/features/users/StaffPage";
import { DepartmentsPage } from "@/features/organization/DepartmentsPage";
import { ClassesPage } from "@/features/organization/ClassesPage";
import { TopicsPage } from "@/features/topics/TopicsPage";
import { QuestionsPage } from "@/features/questions/QuestionsPage";
import { ProblemsPage } from "@/features/problems/ProblemsPage";
import { ExamTypesPage } from "@/features/exams/ExamTypesPage";
import { ExamsPage } from "@/features/exams/ExamsPage";
import { ExamSlotsPage } from "@/features/exams/ExamSlotsPage";
import { QuizzesPage } from "@/features/quizzes/QuizzesPage";
import { RedeemInvitationPage } from "@/features/auth/RedeemInvitationPage";
import { ApplicationsPage } from "@/features/applications/ApplicationsPage";
import { StudentEntrancePage } from "@/features/students/StudentEntrancePage";
import { ApplyEntrancePage } from "@/features/students/ApplyEntrancePage";
import { PublicExamPage } from "@/features/students/PublicExamPage";
import { StudentQuizzesPage } from "@/features/students/StudentQuizzesPage";
import { StudentsPage } from "@/features/students/StudentsPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/signup", element: <SignupPage /> },
  { path: "/redeem-invitation", element: <RedeemInvitationPage /> },
  { path: "/e/:slug", element: <PublicExamPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/dashboard", element: <DashboardPage /> },
          { path: "/entrance", element: <StudentEntrancePage /> },
          { path: "/entrance/apply", element: <ApplyEntrancePage /> },
          { path: "/student-quizzes", element: <StudentQuizzesPage /> },

          // super_admin only
          {
            element: <ProtectedRoute allowedRoles={["super_admin"]} />,
            children: [
              { path: "/colleges", element: <CollegesPage /> },
              { path: "/admins", element: <AdminsPage /> },
              { path: "/exam-types", element: <ExamTypesPage /> },
            ],
          },

          // admin + super_admin
          {
            element: <ProtectedRoute allowedRoles={["super_admin", "admin"]} />,
            children: [
              { path: "/departments", element: <DepartmentsPage /> },
              { path: "/staff", element: <StaffPage /> },
              { path: "/students", element: <StudentsPage /> },
              { path: "/applications", element: <ApplicationsPage /> },
            ],
          },

          // Admin and staff content management
          {
            element: <ProtectedRoute allowedRoles={["admin", "staff"]} />,
            children: [
              { path: "/classes", element: <ClassesPage /> },
              { path: "/topics", element: <TopicsPage /> },
              { path: "/questions", element: <QuestionsPage /> },
              { path: "/problems", element: <ProblemsPage /> },
              { path: "/exams", element: <ExamsPage /> },
              { path: "/exam-slots", element: <ExamSlotsPage /> },
              { path: "/quizzes", element: <QuizzesPage /> },
            ],
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
