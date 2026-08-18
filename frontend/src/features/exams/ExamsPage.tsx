import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileSpreadsheet, Plus, Pencil, Trash2, Settings2, Calendar, Wallet } from "lucide-react";
import toast from "react-hot-toast";
import { examsApi, examTypesApi } from "@/api/exams";
import { apiErrorMessage } from "@/api/client";
import type { ExamCreate, ExamOut, ExamStatus } from "@/types/exam";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Select } from "@/components/ui/Select";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Badge, type BadgeProps } from "@/components/ui/Badge";
import { formatCurrency, formatDateTime, toDatetimeLocalValue } from "@/lib/utils";
import { ExamConfigModal } from "./ExamConfigModal";

const STATUS_VARIANT: Record<string, BadgeProps["variant"]> = {
  draft: "neutral",
  published: "brand",
  running: "success",
  completed: "accent",
  cancelled: "danger",
};

const STATUS_OPTIONS: { value: ExamStatus; label: string }[] = [
  { value: "draft", label: "Draft" },
  { value: "published", label: "Published" },
  { value: "running", label: "Running" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

const emptyForm: ExamCreate = {
  name: "",
  description: "",
  exam_type_id: 0,
  starts_at: "",
  ends_at: "",
  duration_minutes: undefined,
  fee: undefined,
  fee_currency: "INR",
  status: "draft",
};

export function ExamsPage() {
  const queryClient = useQueryClient();
  const { data: exams = [], isLoading } = useQuery({ queryKey: ["exams"], queryFn: () => examsApi.list() });
  const { data: examTypes = [] } = useQuery({ queryKey: ["exam-types"], queryFn: () => examTypesApi.list() });
  const typeMap = new Map(examTypes.map((t) => [t.id, t.name]));

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ExamOut | null>(null);
  const [form, setForm] = useState<ExamCreate>(emptyForm);
  const [deleting, setDeleting] = useState<ExamOut | null>(null);
  const [configuring, setConfiguring] = useState<ExamOut | null>(null);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  }
  function openEdit(exam: ExamOut) {
    setEditing(exam);
    setForm({
      name: exam.name,
      description: exam.description ?? "",
      exam_type_id: exam.exam_type_id,
      starts_at: toDatetimeLocalValue(exam.starts_at),
      ends_at: toDatetimeLocalValue(exam.ends_at),
      duration_minutes: exam.duration_minutes ?? undefined,
      fee: exam.fee ?? undefined,
      fee_currency: exam.fee_currency,
      status: (exam.status as ExamStatus) ?? "draft",
    });
    setModalOpen(true);
  }

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload: ExamCreate = {
        ...form,
        starts_at: form.starts_at || null,
        ends_at: form.ends_at || null,
        duration_minutes: form.duration_minutes || null,
        fee: form.fee || null,
      };
      return editing ? examsApi.update(editing.id, payload) : examsApi.create(payload);
    },
    onSuccess: () => {
      toast.success(editing ? "Exam updated" : "Exam created");
      queryClient.invalidateQueries({ queryKey: ["exams"] });
      setModalOpen(false);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not save exam")),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => examsApi.remove(id),
    onSuccess: () => {
      toast.success("Exam deleted");
      queryClient.invalidateQueries({ queryKey: ["exams"] });
      setDeleting(null);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not delete exam")),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    saveMutation.mutate();
  }

  const columns: Column<ExamOut>[] = [
    {
      header: "Exam",
      accessor: (e) => (
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500/20 to-accent-500/20 text-brand-300 ring-1 ring-inset ring-brand-500/20">
            <FileSpreadsheet className="size-4" />
          </div>
          <div>
            <p className="font-medium text-slate-100">{e.name}</p>
            <p className="text-xs text-slate-500">{typeMap.get(e.exam_type_id) ?? e.exam_type_name ?? "—"}</p>
          </div>
        </div>
      ),
    },
    {
      header: "Schedule",
      accessor: (e) => (
        <div className="space-y-0.5 text-xs text-slate-400">
          <p className="flex items-center gap-1.5">
            <Calendar className="size-3" /> {formatDateTime(e.starts_at)}
          </p>
          {e.duration_minutes && <p className="text-slate-600">{e.duration_minutes} min</p>}
        </div>
      ),
    },
    {
      header: "Fee",
      accessor: (e) => (
        <span className="flex items-center gap-1.5 text-sm text-slate-300">
          <Wallet className="size-3.5 text-slate-500" /> {formatCurrency(e.fee, e.fee_currency)}
        </span>
      ),
    },
    {
      header: "Status",
      accessor: (e) => (
        <Badge variant={STATUS_VARIANT[e.status ?? "draft"]} dot>
          {e.status ?? "draft"}
        </Badge>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Exams"
        description="Create and configure entrance exams — quizzes, topic weightage, and schedule."
        actions={
          <Button onClick={openCreate}>
            <Plus className="size-4" /> New Exam
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={exams}
        keyExtractor={(e) => e.id}
        loading={isLoading}
        emptyTitle="No exams yet"
        emptyDescription="Create an exam type first, then set up your first exam."
        rowActions={(e) => (
          <>
            <button
              onClick={() => setConfiguring(e)}
              title="Configure quizzes & topic weights"
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <Settings2 className="size-4" />
            </button>
            <button
              onClick={() => openEdit(e)}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <Pencil className="size-4" />
            </button>
            <button
              onClick={() => setDeleting(e)}
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
        title={editing ? "Edit Exam" : "New Exam"}
        size="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Exam name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Textarea
            label="Description"
            value={form.description ?? ""}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Select
              label="Exam type"
              required
              placeholder="Select exam type"
              value={form.exam_type_id ? String(form.exam_type_id) : ""}
              onChange={(e) => setForm({ ...form, exam_type_id: Number(e.target.value) })}
              options={examTypes.map((t) => ({ value: String(t.id), label: t.name }))}
            />
            <Select
              label="Status"
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value as ExamStatus })}
              options={STATUS_OPTIONS}
            />
            <Input
              label="Starts at"
              type="datetime-local"
              value={form.starts_at ?? ""}
              onChange={(e) => setForm({ ...form, starts_at: e.target.value })}
            />
            <Input
              label="Ends at"
              type="datetime-local"
              value={form.ends_at ?? ""}
              onChange={(e) => setForm({ ...form, ends_at: e.target.value })}
            />
            <Input
              label="Duration (minutes)"
              type="number"
              min={1}
              value={form.duration_minutes ?? ""}
              onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) || undefined })}
            />
            <div className="grid grid-cols-[1fr_auto] gap-2">
              <Input
                label="Fee"
                type="number"
                min={0}
                step="0.01"
                value={form.fee ?? ""}
                onChange={(e) => setForm({ ...form, fee: Number(e.target.value) || undefined })}
              />
              <Input
                label="Currency"
                className="w-20"
                value={form.fee_currency}
                onChange={(e) => setForm({ ...form, fee_currency: e.target.value })}
              />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="glass" className="flex-1" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" className="flex-1" loading={saveMutation.isPending}>
              {editing ? "Save Changes" : "Create Exam"}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title={`Delete ${deleting?.name}?`}
        description="Exams with registrations, quizzes, or attempts linked can't be deleted."
        confirmLabel="Delete"
        loading={deleteMutation.isPending}
      />

      {configuring && (
        <ExamConfigModal exam={configuring} open={!!configuring} onClose={() => setConfiguring(null)} />
      )}
    </div>
  );
}
