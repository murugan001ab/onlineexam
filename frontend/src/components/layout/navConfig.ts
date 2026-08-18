import {
  LayoutDashboard,
  Building2,
  Users,
  GraduationCap,
  BookOpen,
  Code2,
  FileSpreadsheet,
  ClipboardList,
  ListChecks,
  School,
  HelpCircle,
  Layers,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { RoleName } from "@/types/auth";

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
}

export const NAV_BY_ROLE: Record<RoleName, NavItem[]> = {
  // NOTE: super_admin is intentionally NOT given Topics/Questions/Problems/
  // Exams/Quizzes — those tables are college-scoped (college_id NOT NULL)
  // and super_admin has no college_id, so those create endpoints would 500
  // for a super_admin caller. super_admin manages colleges + admins only;
  // Exam Types is the one global (non-college-scoped) content table.
  super_admin: [
    { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
    { label: "Colleges", to: "/colleges", icon: Building2 },
    { label: "Admins", to: "/admins", icon: Users },
    { label: "Exam Types", to: "/exam-types", icon: Layers },
  ],
  admin: [
    { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
    { label: "Departments", to: "/departments", icon: School },
    { label: "Classes", to: "/classes", icon: GraduationCap },
    { label: "Staff", to: "/staff", icon: Users },
    { label: "Topics", to: "/topics", icon: BookOpen },
    { label: "Questions", to: "/questions", icon: HelpCircle },
    { label: "Problems", to: "/problems", icon: Code2 },
    { label: "Exams", to: "/exams", icon: FileSpreadsheet },
    { label: "Quizzes", to: "/quizzes", icon: ListChecks },
    { label: "Submissions", to: "/submissions", icon: ClipboardList },
  ],
  staff: [
    { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
    { label: "My Classes", to: "/classes", icon: GraduationCap },
    { label: "Topics", to: "/topics", icon: BookOpen },
    { label: "Questions", to: "/questions", icon: HelpCircle },
    { label: "Problems", to: "/problems", icon: Code2 },
    { label: "Exams", to: "/exams", icon: FileSpreadsheet },
    { label: "Quizzes", to: "/quizzes", icon: ListChecks },
    { label: "Submissions", to: "/submissions", icon: ClipboardList },
  ],
  student: [
    { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
    { label: "Exams", to: "/exams", icon: FileSpreadsheet },
    { label: "Quizzes", to: "/quizzes", icon: ListChecks },
    { label: "My Results", to: "/results", icon: ClipboardList },
  ],
};
