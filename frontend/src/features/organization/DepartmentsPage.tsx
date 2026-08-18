import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { School, Plus, Pencil, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import { departmentsApi } from "@/api/organization";
import { collegesApi } from "@/api/colleges";
import { apiErrorMessage } from "@/api/client";
import type { DepartmentCreate, DepartmentOut } from "@/types/organization";
import { useAuthStore } from "@/store/authStore";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

export function DepartmentsPage() {
  const currentUser = useAuthStore((s) => s.user);
  const isSuperAdmin = currentUser?.role === "super_admin";
  const queryClient = useQueryClient();

  const { data: departments = [], isLoading } = useQuery({
    queryKey: ["departments"],
    queryFn: () => departmentsApi.list(),
  });

  const { data: colleges = [] } = useQuery({
    queryKey: ["colleges"],
    queryFn: () => collegesApi.list({ is_active: true }),
    enabled: isSuperAdmin,
  });

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<DepartmentOut | null>(null);
  const [form, setForm] = useState<DepartmentCreate>({ name: "", code: "", college_id: undefined });
  const [deleting, setDeleting] = useState<DepartmentOut | null>(null);

  function openCreate() {
    setEditing(null);
    setForm({ name: "", code: "", college_id: undefined });
    setModalOpen(true);
  }
  function openEdit(dept: DepartmentOut) {
    setEditing(dept);
    setForm({ name: dept.name, code: dept.code ?? "", college_id: dept.college_id });
    setModalOpen(true);
  }

  const saveMutation = useMutation({
    mutationFn: () =>
      editing
        ? departmentsApi.update(editing.id, { name: form.name, code: form.code || null })
        : departmentsApi.create(form),
    onSuccess: () => {
      toast.success(editing ? "Department updated" : "Department created");
      queryClient.invalidateQueries({ queryKey: ["departments"] });
      setModalOpen(false);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not save department")),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => departmentsApi.remove(id),
    onSuccess: () => {
      toast.success("Department deleted");
      queryClient.invalidateQueries({ queryKey: ["departments"] });
      setDeleting(null);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not delete department")),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    saveMutation.mutate();
  }

  const columns: Column<DepartmentOut>[] = [
    {
      header: "Department",
      accessor: (d) => (
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500/20 to-accent-500/20 text-brand-300 ring-1 ring-inset ring-brand-500/20">
            <School className="size-4" />
          </div>
          <div>
            <p className="font-medium text-slate-100">{d.name}</p>
            {d.code && <p className="text-xs text-slate-500">{d.code}</p>}
          </div>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Departments"
        description="Organize your college into departments."
        actions={
          <Button onClick={openCreate}>
            <Plus className="size-4" /> New Department
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={departments}
        keyExtractor={(d) => d.id}
        loading={isLoading}
        emptyTitle="No departments yet"
        rowActions={(d) => (
          <>
            <button
              onClick={() => openEdit(d)}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <Pencil className="size-4" />
            </button>
            <button
              onClick={() => setDeleting(d)}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-danger-500/10 hover:text-danger-500"
            >
              <Trash2 className="size-4" />
            </button>
          </>
        )}
      />

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? "Edit Department" : "New Department"}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Department name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Input
            label="Code"
            value={form.code ?? ""}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
          />
          {isSuperAdmin && !editing && (
            <Select
              label="College"
              required
              placeholder="Select a college"
              value={form.college_id ? String(form.college_id) : ""}
              onChange={(e) => setForm({ ...form, college_id: Number(e.target.value) })}
              options={colleges.map((c) => ({ value: String(c.id), label: c.name }))}
            />
          )}
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="glass" className="flex-1" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" className="flex-1" loading={saveMutation.isPending}>
              {editing ? "Save Changes" : "Create Department"}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title={`Delete ${deleting?.name}?`}
        description="This can't be undone. Departments with classes or staff assignments can't be deleted."
        confirmLabel="Delete"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
