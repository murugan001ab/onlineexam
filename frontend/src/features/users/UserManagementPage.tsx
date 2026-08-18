import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Mail, Phone, Plus, Pencil, Power, UserCog, ShieldCheck } from "lucide-react";
import toast from "react-hot-toast";
import { usersApi } from "@/api/users";
import { collegesApi } from "@/api/colleges";
import { apiErrorMessage } from "@/api/client";
import type { ManagedRole, UserCreate, UserOut } from "@/types/user";
import { useAuthStore } from "@/store/authStore";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Badge } from "@/components/ui/Badge";
import { getInitials } from "@/lib/utils";
import { StaffAssignmentsModal } from "./StaffAssignmentsModal";

interface FormState {
  username: string;
  email: string;
  password: string;
  college_id: string;
  name: string;
  phone: string;
  gender: string;
}

const emptyForm: FormState = {
  username: "",
  email: "",
  password: "",
  college_id: "",
  name: "",
  phone: "",
  gender: "",
};

interface UserManagementPageProps {
  managedRole: ManagedRole;
  title: string;
  description: string;
}

export function UserManagementPage({ managedRole, title, description }: UserManagementPageProps) {
  const currentUser = useAuthStore((s) => s.user);
  const isSuperAdmin = currentUser?.role === "super_admin";
  const queryClient = useQueryClient();

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["users", managedRole],
    queryFn: () => usersApi.list({ role: managedRole }),
  });

  const { data: colleges = [] } = useQuery({
    queryKey: ["colleges"],
    queryFn: () => collegesApi.list({ is_active: true }),
    enabled: isSuperAdmin,
  });

  const collegeMap = useMemo(
    () => new Map(colleges.map((c) => [c.id, c.name])),
    [colleges],
  );

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<UserOut | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [deactivating, setDeactivating] = useState<UserOut | null>(null);
  const [assigning, setAssigning] = useState<UserOut | null>(null);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  }

  function openEdit(user: UserOut) {
    setEditing(user);
    setForm({
      username: user.username,
      email: user.email ?? "",
      password: "",
      college_id: String(user.college_id ?? ""),
      name: user.profile?.name ?? "",
      phone: user.profile?.phone ?? "",
      gender: user.profile?.gender ?? "",
    });
    setModalOpen(true);
  }

  const saveMutation = useMutation({
    mutationFn: () => {
      if (editing) {
        return usersApi.update(editing.id, {
          email: form.email || null,
          password: form.password || undefined,
          college_id: isSuperAdmin && form.college_id ? Number(form.college_id) : undefined,
          profile: { name: form.name, phone: form.phone || null, gender: form.gender || null },
        });
      }
      const payload: UserCreate = {
        username: form.username,
        email: form.email || undefined,
        password: form.password,
        role: managedRole,
        college_id: isSuperAdmin ? Number(form.college_id) : undefined,
        profile: { name: form.name, phone: form.phone || undefined, gender: form.gender || undefined },
      };
      return usersApi.create(payload);
    },
    onSuccess: () => {
      toast.success(editing ? "User updated" : "User created");
      queryClient.invalidateQueries({ queryKey: ["users", managedRole] });
      setModalOpen(false);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not save user")),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: number) => usersApi.deactivate(id),
    onSuccess: () => {
      toast.success("User deactivated");
      queryClient.invalidateQueries({ queryKey: ["users", managedRole] });
      setDeactivating(null);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not deactivate user")),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    saveMutation.mutate();
  }

  const columns: Column<UserOut>[] = [
    {
      header: "Name",
      accessor: (u) => (
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-accent-500 text-xs font-bold text-white">
            {getInitials(u.profile?.name || u.username)}
          </div>
          <div>
            <p className="font-medium text-slate-100">{u.profile?.name || u.username}</p>
            <p className="text-xs text-slate-500">@{u.username}</p>
          </div>
        </div>
      ),
    },
    {
      header: "Contact",
      accessor: (u) => (
        <div className="space-y-1 text-xs">
          {u.email && (
            <p className="flex items-center gap-1.5">
              <Mail className="size-3 text-slate-500" /> {u.email}
            </p>
          )}
          {u.profile?.phone && (
            <p className="flex items-center gap-1.5">
              <Phone className="size-3 text-slate-500" /> {u.profile.phone}
            </p>
          )}
        </div>
      ),
    },
    ...(isSuperAdmin
      ? [
          {
            header: "College",
            accessor: (u: UserOut) => (
              <span className="text-sm text-slate-400">
                {u.college_id ? (collegeMap.get(u.college_id) ?? `#${u.college_id}`) : "—"}
              </span>
            ),
          } as Column<UserOut>,
        ]
      : []),
    {
      header: "Status",
      accessor: (u) => (
        <Badge variant={u.is_active ? "success" : "neutral"} dot>
          {u.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title={title}
        description={description}
        actions={
          <Button onClick={openCreate}>
            <Plus className="size-4" /> Add {managedRole === "admin" ? "Admin" : "Staff"}
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={users}
        keyExtractor={(u) => u.id}
        loading={isLoading}
        emptyTitle={`No ${managedRole}s yet`}
        emptyDescription={`Add your first ${managedRole} account to get started.`}
        rowActions={(u) => (
          <>
            {managedRole === "staff" && (
              <button
                onClick={() => setAssigning(u)}
                title="Manage assignments"
                className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
              >
                <UserCog className="size-4" />
              </button>
            )}
            <button
              onClick={() => openEdit(u)}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <Pencil className="size-4" />
            </button>
            {u.is_active && (
              <button
                onClick={() => setDeactivating(u)}
                className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-danger-500/10 hover:text-danger-500"
              >
                <Power className="size-4" />
              </button>
            )}
          </>
        )}
      />

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? "Edit User" : `New ${managedRole === "admin" ? "Admin" : "Staff"} Account`}
        description={
          editing
            ? `Editing ${editing.username}`
            : isSuperAdmin
              ? "Choose a college and set up login credentials."
              : "Sets up a login for a staff member in your college."
        }
        size="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input
              label="Full name"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <Input
              label="Username"
              required
              disabled={!!editing}
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
            />
            <Input
              label="Email"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
            <Input
              label="Phone"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
            <Input
              label={editing ? "New password (optional)" : "Password"}
              type="password"
              required={!editing}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
            {isSuperAdmin && (
              <Select
                label="College"
                required
                placeholder="Select a college"
                value={form.college_id}
                onChange={(e) => setForm({ ...form, college_id: e.target.value })}
                options={colleges.map((c) => ({ value: String(c.id), label: c.name }))}
              />
            )}
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-brand-500/20 bg-brand-500/5 px-3.5 py-2.5 text-xs text-brand-300">
            <ShieldCheck className="size-4 shrink-0" />
            This account will be created with the <strong className="font-semibold">{managedRole}</strong> role.
          </div>
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="glass" className="flex-1" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" className="flex-1" loading={saveMutation.isPending}>
              {editing ? "Save Changes" : "Create Account"}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!deactivating}
        onClose={() => setDeactivating(null)}
        onConfirm={() => deactivating && deactivateMutation.mutate(deactivating.id)}
        title={`Deactivate ${deactivating?.username}?`}
        description="They'll immediately lose the ability to sign in. This can be reversed later."
        confirmLabel="Deactivate"
        loading={deactivateMutation.isPending}
      />

      {assigning && (
        <StaffAssignmentsModal
          staff={assigning}
          open={!!assigning}
          onClose={() => setAssigning(null)}
        />
      )}
    </div>
  );
}
