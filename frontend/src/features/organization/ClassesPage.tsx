import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GraduationCap, Plus, Pencil, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import { classesApi, departmentsApi } from "@/api/organization";
import { apiErrorMessage } from "@/api/client";
import type { ClassCreate, ClassOut } from "@/types/organization";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Badge } from "@/components/ui/Badge";

const emptyForm: ClassCreate = { department_id: 0, name: "", academic_year: "", section: "" };

export function ClassesPage() {
  const queryClient = useQueryClient();

  const { data: classes = [], isLoading } = useQuery({
    queryKey: ["classes"],
    queryFn: () => classesApi.list(),
  });
  const { data: departments = [] } = useQuery({
    queryKey: ["departments"],
    queryFn: () => departmentsApi.list(),
  });
  const deptMap = new Map(departments.map((d) => [d.id, d.name]));

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ClassOut | null>(null);
  const [form, setForm] = useState<ClassCreate>(emptyForm);
  const [deleting, setDeleting] = useState<ClassOut | null>(null);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  }
  function openEdit(klass: ClassOut) {
    setEditing(klass);
    setForm({
      department_id: klass.department_id,
      name: klass.name,
      academic_year: klass.academic_year ?? "",
      section: klass.section ?? "",
    });
    setModalOpen(true);
  }

  const saveMutation = useMutation({
    mutationFn: () =>
      editing
        ? classesApi.update(editing.id, {
            name: form.name,
            academic_year: form.academic_year || null,
            section: form.section || null,
          })
        : classesApi.create(form),
    onSuccess: () => {
      toast.success(editing ? "Class updated" : "Class created");
      queryClient.invalidateQueries({ queryKey: ["classes"] });
      setModalOpen(false);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not save class")),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => classesApi.remove(id),
    onSuccess: () => {
      toast.success("Class deleted");
      queryClient.invalidateQueries({ queryKey: ["classes"] });
      setDeleting(null);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not delete class")),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    saveMutation.mutate();
  }

  const columns: Column<ClassOut>[] = [
    {
      header: "Class",
      accessor: (c) => (
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-accent-500/20 to-brand-500/20 text-accent-300 ring-1 ring-inset ring-accent-500/20">
            <GraduationCap className="size-4" />
          </div>
          <div>
            <p className="font-medium text-slate-100">{c.name}</p>
            <p className="text-xs text-slate-500">{deptMap.get(c.department_id) ?? `Dept #${c.department_id}`}</p>
          </div>
        </div>
      ),
    },
    {
      header: "Details",
      accessor: (c) => (
        <div className="flex gap-1.5">
          {c.academic_year && <Badge variant="neutral">{c.academic_year}</Badge>}
          {c.section && <Badge variant="accent">Sec {c.section}</Badge>}
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Classes"
        description="Manage classes within your departments."
        actions={
          <Button onClick={openCreate}>
            <Plus className="size-4" /> New Class
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={classes}
        keyExtractor={(c) => c.id}
        loading={isLoading}
        emptyTitle="No classes yet"
        rowActions={(c) => (
          <>
            <button
              onClick={() => openEdit(c)}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <Pencil className="size-4" />
            </button>
            <button
              onClick={() => setDeleting(c)}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-danger-500/10 hover:text-danger-500"
            >
              <Trash2 className="size-4" />
            </button>
          </>
        )}
      />

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit Class" : "New Class"}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {!editing && (
            <Select
              label="Department"
              required
              placeholder="Select a department"
              value={form.department_id ? String(form.department_id) : ""}
              onChange={(e) => setForm({ ...form, department_id: Number(e.target.value) })}
              options={departments.map((d) => ({ value: String(d.id), label: d.name }))}
            />
          )}
          <Input
            label="Class name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Academic year"
              placeholder="2025-26"
              value={form.academic_year ?? ""}
              onChange={(e) => setForm({ ...form, academic_year: e.target.value })}
            />
            <Input
              label="Section"
              placeholder="A"
              value={form.section ?? ""}
              onChange={(e) => setForm({ ...form, section: e.target.value })}
            />
          </div>
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="glass" className="flex-1" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" className="flex-1" loading={saveMutation.isPending}>
              {editing ? "Save Changes" : "Create Class"}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title={`Delete ${deleting?.name}?`}
        description="This can't be undone. Classes with enrolled students or assignments can't be deleted."
        confirmLabel="Delete"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
