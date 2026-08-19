import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { CalendarClock, Pencil, Plus, Users2, XCircle } from "lucide-react";
import toast from "react-hot-toast";
import { examSlotsApi, examsApi } from "@/api/exams";
import { apiErrorMessage } from "@/api/client";
import type { ExamSlotCreate, ExamSlotOut, SlotStatus } from "@/types/exam";
import { Badge, type BadgeProps } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { formatDateTime, toDatetimeLocalValue } from "@/lib/utils";

const STATUS_VARIANT: Record<string, BadgeProps["variant"]> = {
  open: "success",
  closed: "warning",
  cancelled: "danger",
};

const STATUS_OPTIONS: { value: SlotStatus; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "closed", label: "Closed" },
  { value: "cancelled", label: "Cancelled" },
];

function emptyForm(examId: number): ExamSlotCreate {
  return {
    exam_id: examId,
    name: "",
    starts_at: "",
    ends_at: "",
    max_capacity: 30,
    status: "open",
  };
}

export function ExamSlotsPage() {
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const { data: exams = [], isLoading: loadingExams } = useQuery({
    queryKey: ["exams-for-slots"],
    queryFn: () => examsApi.list(),
  });
  // Deep-linkable via /exam-slots?exam=123 (used by "Manage slots" in
  // ExamConfigModal) so admins land on the right exam instead of having to
  // reselect it from the dropdown.
  const examIdFromUrl = Number(searchParams.get("exam")) || null;
  const [examId, setExamId] = useState<number | null>(examIdFromUrl);
  const activeExamId = examId ?? examIdFromUrl ?? exams[0]?.id ?? null;

  function selectExam(id: number | null) {
    setExamId(id);
    setSearchParams(id ? { exam: String(id) } : {}, { replace: true });
  }

  const { data: slots = [], isLoading } = useQuery({
    queryKey: ["exam-slots", activeExamId],
    queryFn: () => examSlotsApi.list({ exam_id: activeExamId! }),
    enabled: !!activeExamId,
  });

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ExamSlotOut | null>(null);
  const [form, setForm] = useState<ExamSlotCreate>(emptyForm(0));
  const [cancelling, setCancelling] = useState<ExamSlotOut | null>(null);

  function openCreate() {
    if (!activeExamId) return;
    setEditing(null);
    setForm(emptyForm(activeExamId));
    setOpen(true);
  }

  function openEdit(slot: ExamSlotOut) {
    setEditing(slot);
    setForm({
      exam_id: slot.exam_id ?? activeExamId!,
      name: slot.name ?? "",
      starts_at: toDatetimeLocalValue(slot.starts_at),
      ends_at: toDatetimeLocalValue(slot.ends_at),
      max_capacity: slot.max_capacity,
      status: (slot.status as SlotStatus) ?? "open",
    });
    setOpen(true);
  }

  const save = useMutation({
    mutationFn: () => {
      const payload: ExamSlotCreate = {
        ...form,
        starts_at: new Date(form.starts_at).toISOString(),
        ends_at: new Date(form.ends_at).toISOString(),
      };
      return editing ? examSlotsApi.update(editing.id, payload) : examSlotsApi.create(payload);
    },
    onSuccess: () => {
      toast.success(editing ? "Slot updated" : "Slot created");
      qc.invalidateQueries({ queryKey: ["exam-slots", activeExamId] });
      setOpen(false);
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not save slot")),
  });

  const cancelSlot = useMutation({
    mutationFn: (id: number) => examSlotsApi.cancel(id),
    onSuccess: () => {
      toast.success("Slot cancelled");
      qc.invalidateQueries({ queryKey: ["exam-slots", activeExamId] });
      setCancelling(null);
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not cancel slot")),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!form.starts_at || !form.ends_at) {
      toast.error("Set both a start and end time for the slot.");
      return;
    }
    if (new Date(form.ends_at) <= new Date(form.starts_at)) {
      toast.error("End time must be after the start time.");
      return;
    }
    save.mutate();
  }

  // Group slots by calendar day so admins can see "how many slots today /
  // this date" at a glance, same idea as a booking-day view.
  const slotsByDay = groupByDay(slots);

  const columns: Column<ExamSlotOut>[] = [
    {
      header: "Slot",
      accessor: (s) => (
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500/20 to-accent-500/20 text-brand-300 ring-1 ring-inset ring-brand-500/20">
            <CalendarClock className="size-4" />
          </div>
          <div>
            <p className="font-medium text-slate-100">{s.name || `Slot #${s.id}`}</p>
            <p className="text-xs text-slate-500">
              {formatDateTime(s.starts_at)} &ndash; {formatDateTime(s.ends_at)}
            </p>
          </div>
        </div>
      ),
    },
    {
      header: "Capacity",
      accessor: (s) => (
        <span className="flex items-center gap-1.5 text-sm text-slate-300">
          <Users2 className="size-3.5 text-slate-500" />
          {s.booked_count} / {s.max_capacity} booked
          <span className="text-slate-600">({s.available} left)</span>
        </span>
      ),
    },
    {
      header: "Status",
      accessor: (s) => (
        <Badge variant={STATUS_VARIANT[s.status ?? "open"]} dot>
          {s.status ?? "open"}
        </Badge>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Exam Slots"
        description="Set how many booking slots run on a given day and how many students each slot can hold, per exam. Students only see slots created for the exam they're applying to."
        actions={
          <Button onClick={openCreate} disabled={!activeExamId}>
            <Plus className="size-4" /> New Slot
          </Button>
        }
      />

      <div className="max-w-xs">
        <Select
          label="Exam"
          value={activeExamId ? String(activeExamId) : ""}
          onChange={(e) => selectExam(Number(e.target.value) || null)}
          options={exams.map((e) => ({ value: String(e.id), label: e.name }))}
          disabled={loadingExams || exams.length === 0}
        />
        {!loadingExams && exams.length === 0 && (
          <p className="mt-1.5 text-xs text-slate-500">Create an exam first — slots are always created against a specific exam.</p>
        )}
      </div>

      {slotsByDay.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {slotsByDay.map(({ day, count, capacity }) => (
            <div
              key={day}
              className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-slate-400"
            >
              <span className="font-medium text-slate-200">{day}</span> &middot; {count} slot
              {count === 1 ? "" : "s"} &middot; {capacity} seats
            </div>
          ))}
        </div>
      )}

      <DataTable
        columns={columns}
        data={slots}
        keyExtractor={(s) => s.id}
        loading={isLoading}
        emptyTitle="No exam slots yet"
        emptyDescription="Create a slot for each sitting — e.g. 10 slots a day, 40 students per slot."
        rowActions={(s) => (
          <>
            <button
              onClick={() => openEdit(s)}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <Pencil className="size-4" />
            </button>
            {s.status !== "cancelled" && (
              <button
                onClick={() => setCancelling(s)}
                className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-danger-500/10 hover:text-danger-500"
              >
                <XCircle className="size-4" />
              </button>
            )}
          </>
        )}
      />

      <Modal open={open} onClose={() => setOpen(false)} title={editing ? "Edit Slot" : "New Slot"} size="md">
        <form onSubmit={submit} className="space-y-4">
          <Input
            label="Slot name (optional)"
            placeholder="e.g. Morning batch — Hall A"
            value={form.name ?? ""}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input
              label="Starts at"
              type="datetime-local"
              required
              value={form.starts_at}
              onChange={(e) => setForm({ ...form, starts_at: e.target.value })}
            />
            <Input
              label="Ends at"
              type="datetime-local"
              required
              value={form.ends_at}
              onChange={(e) => setForm({ ...form, ends_at: e.target.value })}
            />
            <Input
              label="Max students in this slot"
              type="number"
              min={1}
              required
              value={form.max_capacity}
              onChange={(e) => setForm({ ...form, max_capacity: Number(e.target.value) || 1 })}
            />
            <Select
              label="Status"
              value={form.status ?? "open"}
              onChange={(e) => setForm({ ...form, status: e.target.value as SlotStatus })}
              options={STATUS_OPTIONS}
            />
          </div>
          {editing && editing.booked_count > 0 && (
            <p className="text-xs text-slate-500">
              {editing.booked_count} student(s) already booked into this slot — capacity can&apos;t be
              reduced below that.
            </p>
          )}
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="glass" className="flex-1" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" className="flex-1" loading={save.isPending}>
              {editing ? "Save Changes" : "Create Slot"}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!cancelling}
        onClose={() => setCancelling(null)}
        onConfirm={() => cancelling && cancelSlot.mutate(cancelling.id)}
        title={`Cancel ${cancelling?.name || `slot #${cancelling?.id}`}?`}
        description="Existing bookings against this slot stay on record, but no new students can be assigned to it."
        confirmLabel="Cancel slot"
        loading={cancelSlot.isPending}
      />
    </div>
  );
}

function groupByDay(slots: ExamSlotOut[]) {
  const map = new Map<string, { day: string; count: number; capacity: number }>();
  for (const s of slots) {
    if (s.status === "cancelled") continue;
    const day = new Date(s.starts_at).toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
    const entry = map.get(day) ?? { day, count: 0, capacity: 0 };
    entry.count += 1;
    entry.capacity += s.max_capacity;
    map.set(day, entry);
  }
  return [...map.values()].sort((a, b) => a.day.localeCompare(b.day));
}
