import { UserManagementPage } from "./UserManagementPage";

export function StaffPage() {
  return (
    <UserManagementPage
      managedRole="staff"
      title="Staff"
      description="Staff can be assigned to departments and classes to manage quizzes and grading."
    />
  );
}
