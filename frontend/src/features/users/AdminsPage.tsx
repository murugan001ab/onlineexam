import { UserManagementPage } from "./UserManagementPage";

export function AdminsPage() {
  return (
    <UserManagementPage
      managedRole="admin"
      title="College Admins"
      description="Admins manage a single college's departments, staff, and exams."
    />
  );
}
