import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar, ClipboardCheck, ListChecks, Pencil, Plus, Settings2, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import { quizzesApi } from "@/api/quizzes";
import { apiErrorMessage } from "@/api/client";
import type { QuizCreate, QuizOut, QuizStatus, QuizType } from "@/types/quiz";
import { Badge, type BadgeProps } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { formatDateTime, toDatetimeLocalValue } from "@/lib/utils";
import { QuizConfigModal } from "./QuizConfigModal";

const emptyForm: QuizCreate = { name: "", description: "", quiz_type: "class", subject: "", schedule_start: "", schedule_end: "", duration_minutes: undefined, status: "draft" };
const variants: Record<string, BadgeProps["variant"]> = { draft: "neutral", published: "brand", archived: "danger" };

export function QuizzesPage() {
  const qc = useQueryClient(); const navigate = useNavigate(); const { data: quizzes = [], isLoading } = useQuery({ queryKey: ["quizzes"], queryFn: () => quizzesApi.list() });
  const [open, setOpen] = useState(false); const [editing, setEditing] = useState<QuizOut | null>(null); const [form, setForm] = useState<QuizCreate>(emptyForm); const [deleting, setDeleting] = useState<QuizOut | null>(null); const [configuring, setConfiguring] = useState<QuizOut | null>(null);
  function openCreate() { setEditing(null); setForm(emptyForm); setOpen(true); }
  function openEdit(quiz: QuizOut) { setEditing(quiz); setForm({ name: quiz.name, description: quiz.description ?? "", quiz_type: quiz.quiz_type as QuizType, subject: quiz.subject ?? "", schedule_start: toDatetimeLocalValue(quiz.schedule_start), schedule_end: toDatetimeLocalValue(quiz.schedule_end), duration_minutes: quiz.duration_minutes ?? undefined, status: (quiz.status as QuizStatus) ?? "draft" }); setOpen(true); }
  const save = useMutation({ mutationFn: () => { const payload = { ...form, schedule_start: form.schedule_start || null, schedule_end: form.schedule_end || null, duration_minutes: form.duration_minutes || null }; return editing ? quizzesApi.update(editing.id, payload) : quizzesApi.create(payload); }, onSuccess: () => { toast.success(editing ? "Quiz updated" : "Quiz created"); qc.invalidateQueries({ queryKey: ["quizzes"] }); setOpen(false); }, onError: (e) => toast.error(apiErrorMessage(e, "Could not save quiz")) });
  const remove = useMutation({ mutationFn: (id: number) => quizzesApi.remove(id), onSuccess: () => { toast.success("Quiz deleted"); qc.invalidateQueries({ queryKey: ["quizzes"] }); setDeleting(null); }, onError: (e) => toast.error(apiErrorMessage(e, "Could not delete quiz")) });
  const columns: Column<QuizOut>[] = [
    { header: "Quiz", accessor: (q) => <div className="flex items-center gap-3"><div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500/20 to-accent-500/20 text-brand-300"><ListChecks className="size-4" /></div><div><p className="font-medium text-slate-100">{q.name}</p><p className="text-xs text-slate-500">{q.subject || q.quiz_type || "—"}</p></div></div> },
    { header: "Questions", accessor: (q) => <Badge variant="accent">{q.question_count}</Badge> },
    { header: "Schedule", accessor: (q) => <span className="flex items-center gap-1 text-xs text-slate-400"><Calendar className="size-3" />{formatDateTime(q.schedule_start)}</span> },
    { header: "Status", accessor: (q) => <Badge variant={variants[q.status ?? "draft"] ?? "neutral"} dot>{q.status ?? "draft"}</Badge> },
  ];
  function submit(e: FormEvent) { e.preventDefault(); save.mutate(); }
  return <div><PageHeader title="Quizzes" description="Build class, entrance, and placement quizzes from your question bank." actions={<Button onClick={openCreate}><Plus className="size-4" /> New Quiz</Button>} /><DataTable columns={columns} data={quizzes} keyExtractor={(q) => q.id} loading={isLoading} emptyTitle="No quizzes yet" emptyDescription="Create a quiz, then add its questions and targets." rowActions={(q) => <><button title="Attempts" onClick={() => navigate(`/quizzes/${q.id}/attempts`)} className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"><ClipboardCheck className="size-4" /></button><button title="Configure" onClick={() => setConfiguring(q)} className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"><Settings2 className="size-4" /></button><button onClick={() => openEdit(q)} className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"><Pencil className="size-4" /></button><button onClick={() => setDeleting(q)} className="rounded-lg p-2 text-slate-400 hover:bg-danger-500/10 hover:text-danger-500"><Trash2 className="size-4" /></button></>} />
  <Modal open={open} onClose={() => setOpen(false)} title={editing ? "Edit Quiz" : "New Quiz"} size="lg"><form onSubmit={submit} className="space-y-4"><Input label="Quiz name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /><Textarea label="Description" value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} /><div className="grid gap-4 sm:grid-cols-2"><Select label="Quiz type" disabled={!!editing} value={form.quiz_type} onChange={(e) => setForm({ ...form, quiz_type: e.target.value as QuizType })} options={[{ value: "class", label: "Class" }, { value: "entrance", label: "Entrance" }, { value: "placement", label: "Placement" }]} /><Select label="Status" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as QuizStatus })} options={[{ value: "draft", label: "Draft" }, { value: "published", label: "Published" }, { value: "archived", label: "Archived" }]} /><Input label="Subject" value={form.subject ?? ""} onChange={(e) => setForm({ ...form, subject: e.target.value })} /><Input label="Duration (minutes)" type="number" min={1} value={form.duration_minutes ?? ""} onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) || undefined })} /><Input label="Starts at" type="datetime-local" value={form.schedule_start ?? ""} onChange={(e) => setForm({ ...form, schedule_start: e.target.value })} /><Input label="Ends at" type="datetime-local" value={form.schedule_end ?? ""} onChange={(e) => setForm({ ...form, schedule_end: e.target.value })} /></div><div className="flex gap-3 pt-2"><Button type="button" variant="glass" className="flex-1" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" className="flex-1" loading={save.isPending}>{editing ? "Save Changes" : "Create Quiz"}</Button></div></form></Modal>
  <ConfirmDialog open={!!deleting} onClose={() => setDeleting(null)} onConfirm={() => deleting && remove.mutate(deleting.id)} title={`Delete ${deleting?.name}?`} description="Quizzes already used by an exam cannot be deleted." confirmLabel="Delete" loading={remove.isPending} />{configuring && <QuizConfigModal quiz={configuring} open onClose={() => setConfiguring(null)} />}</div>;
}
