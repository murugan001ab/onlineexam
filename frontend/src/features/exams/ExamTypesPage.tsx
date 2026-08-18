import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Layers, Plus, Pencil, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import { examTypesApi } from "@/api/exams";
import { apiErrorMessage } from "@/api/client";
import type { ExamTypeCreate, ExamTypeOut } from "@/types/exam";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

const emptyForm: ExamTypeCreate = { name: "", description: "" };

export function ExamTypesPage() {
  const queryClient = useQueryClient();
  const { data: examTypes = [], isLoading } = useQuery({
    queryKey: ["exam-types"],
    queryFn: () => examTypesApi.list(),
  });

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ExamTypeOut | null>(null);
  const [form, setForm] = useState<ExamTypeCreate>(emptyForm);
  const [deleting, setDeleting] = useState<ExamTypeOut | null>(null);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  }
  function openEdit(t: ExamTypeOut) {
    setEditing(t);
    setForm({ name: t.name, description: t.description ?? "" });
    setModalOpen(true);
  }

  const saveMutation = useMutation({
    mutationFn: () => (editing ? examTypesApi.update(editing.id, form) : examTypesApi.create(form)),
    onSuccess: () => {
      toast.success(editing ? "Exam type updated" : "Exam type created");
      queryClient.invalidateQueries({ queryKey: ["exam-types"] });
      setModalOpen(false);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not save exam type")),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => examTypesApi.remove(id),
    onSuccess: () => {
      toast.success("Exam type deleted");
      queryClient.invalidateQueries({ queryKey: ["exam-types"] });
      setDeleting(null);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not delete exam type")),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    saveMutation.mutate();
  }

  const columns: Column<ExamTypeOut>[] = [
    {
      header: "Exam Type",
      accessor: (t) => (
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500/20 to-accent-500/20 text-brand-300 ring-1 ring-inset ring-brand-500/20">
            <Layers className="size-4" />
          </div>
          <div>
            <p className="font-medium text-slate-100">{t.name}</p>
            {t.description && <p className="max-w-md truncate text-xs text-slate-500">{t.description}</p>}
          </div>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Exam Types"
        description="Global categories used to classify entrance exams across every college."
        actions={
          <Button onClick={openCreate}>
            <Plus className="size-4" /> New Exam Type
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={examTypes}
        keyExtractor={(t) => t.id}
        loading={isLoading}
        emptyTitle="No exam types yet"
        rowActions={(t) => (
          <>
            <button
              onClick={() => openEdit(t)}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <Pencil className="size-4" />
            </button>
            <button
              onClick={() => setDeleting(t)}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-danger-500/10 hover:text-danger-500"
            >
              <Trash2 className="size-4" />
            </button>
          </>
        )}
      />

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit Exam Type" : "New Exam Type"}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Textarea
            label="Description"
            value={form.description ?? ""}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="glass" className="flex-1" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" className="flex-1" loading={saveMutation.isPending}>
              {editing ? "Save Changes" : "Create"}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title={`Delete ${deleting?.name}?`}
        description="Exam types still used by an exam can't be deleted."
        confirmLabel="Delete"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
