import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HelpCircle, ImagePlus, Pencil, Plus, Power, Trash2, X } from "lucide-react";
import toast from "react-hot-toast";
import { questionsApi } from "@/api/questions";
import { topicsApi } from "@/api/topics";
import { apiErrorMessage } from "@/api/client";
import type { QuestionCreate, QuestionOut, QuestionType } from "@/types/question";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { Textarea } from "@/components/ui/Textarea";

const QUESTION_TYPE_OPTIONS: { value: QuestionType; label: string }[] = [
  { value: "single_choice", label: "Single choice" },
  { value: "multiple_choice", label: "Multiple choice" },
  { value: "true_false", label: "True / false" },
];

const DIFFICULTY_OPTIONS = [
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
];

const emptyForm: QuestionCreate = {
  text: "",
  question_type: "single_choice",
  options: null,
  correct_answer: null,
  explanation: "",
  image_url: null,
  difficulty: "easy",
  marks: 1,
  is_active: true,
  topic_id: null,
};

/** Turns whatever shape `options` happens to be in the DB (string[] is the
 * only shape the builder writes, but older rows may hold other JSON) into a
 * flat list of option labels the editor can render as rows. */
function toOptionRows(question_type: QuestionType, options: unknown): string[] {
  if (question_type === "true_false") return ["True", "False"];
  if (Array.isArray(options) && options.every((o) => typeof o === "string")) {
    return options.length >= 2 ? options : [...options, "", ""].slice(0, Math.max(2, options.length));
  }
  return ["", ""];
}

/** Matches correct_answer (a string for single_choice/true_false, a string[]
 * for multiple_choice) back to indexes into `rows` so the editor can
 * pre-check the right boxes when editing an existing question. */
function toCorrectIndexes(correct_answer: unknown, rows: string[]): number[] {
  const values = Array.isArray(correct_answer) ? correct_answer : correct_answer != null ? [correct_answer] : [];
  return values
    .map((v) => rows.findIndex((r) => r === v))
    .filter((i) => i >= 0);
}

export function QuestionsPage() {
  const qc = useQueryClient();
  const { data: questions = [], isLoading } = useQuery({ queryKey: ["questions"], queryFn: () => questionsApi.list({ is_active: undefined }) });
  const { data: topics = [] } = useQuery({ queryKey: ["topics"], queryFn: topicsApi.list });

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<QuestionOut | null>(null);
  const [form, setForm] = useState<QuestionCreate>(emptyForm);
  const [optionRows, setOptionRows] = useState<string[]>(["", ""]);
  const [correctIndexes, setCorrectIndexes] = useState<number[]>([]);
  const [deactivating, setDeactivating] = useState<QuestionOut | null>(null);
  const [uploadingImage, setUploadingImage] = useState(false);

  const uploadImage = useMutation({
    mutationFn: (file: File) => questionsApi.uploadImage(file),
    onMutate: () => setUploadingImage(true),
    onSuccess: ({ image_url }) => setForm((f) => ({ ...f, image_url })),
    onError: (e) => toast.error(apiErrorMessage(e, "Could not upload image")),
    onSettled: () => setUploadingImage(false),
  });

  const save = useMutation({
    mutationFn: (p: QuestionCreate) => (editing ? questionsApi.update(editing.id, p) : questionsApi.create(p)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["questions"] });
      toast.success(editing ? "Question updated" : "Question created");
      setOpen(false);
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not save question")),
  });

  const deactivate = useMutation({
    mutationFn: questionsApi.deactivate,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["questions"] });
      setDeactivating(null);
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not deactivate question")),
  });

  function show(q?: QuestionOut) {
    const value = q ?? emptyForm;
    const rows = toOptionRows(value.question_type, value.options);
    setEditing(q ?? null);
    setForm(value);
    setOptionRows(rows);
    setCorrectIndexes(toCorrectIndexes(value.correct_answer, rows));
    setOpen(true);
  }

  // Switching type resets the option set to something valid for that type,
  // rather than leaving stale rows/answers from a different question shape.
  function changeType(question_type: QuestionType) {
    setForm((f) => ({ ...f, question_type }));
    if (question_type === "true_false") {
      setOptionRows(["True", "False"]);
      setCorrectIndexes([]);
    } else if (optionRows.length < 2) {
      setOptionRows(["", ""]);
      setCorrectIndexes([]);
    } else if (question_type === "single_choice") {
      setCorrectIndexes((idx) => idx.slice(0, 1));
    }
  }

  function updateOption(i: number, text: string) {
    setOptionRows((rows) => rows.map((r, idx) => (idx === i ? text : r)));
  }

  function addOption() {
    setOptionRows((rows) => [...rows, ""]);
  }

  function removeOption(i: number) {
    setOptionRows((rows) => rows.filter((_, idx) => idx !== i));
    setCorrectIndexes((idx) => idx.filter((c) => c !== i).map((c) => (c > i ? c - 1 : c)));
  }

  function toggleCorrect(i: number) {
    if (form.question_type === "multiple_choice") {
      setCorrectIndexes((idx) => (idx.includes(i) ? idx.filter((c) => c !== i) : [...idx, i]));
    } else {
      setCorrectIndexes([i]);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    const cleanRows = optionRows.map((r) => r.trim());
    if (cleanRows.some((r) => !r)) {
      toast.error("Every option needs text — remove empty rows instead of leaving them blank.");
      return;
    }
    if (correctIndexes.length === 0) {
      toast.error("Mark at least one option as the correct answer.");
      return;
    }
    const correct_answer =
      form.question_type === "multiple_choice" ? correctIndexes.map((i) => cleanRows[i]) : cleanRows[correctIndexes[0]];
    save.mutate({ ...form, options: cleanRows, correct_answer });
  }

  const cols: Column<QuestionOut>[] = [
    {
      header: "Question",
      accessor: (q) => (
        <div className="flex items-start gap-3">
          <HelpCircle className="mt-1 size-4 text-brand-300" />
          <div>
            <p className="font-medium text-slate-100">{q.text}</p>
            <p className="text-xs text-slate-500">
              {topics.find((t) => t.id === q.topic_id)?.name ?? "No topic"} · {q.question_type?.replaceAll("_", " ")}
              {q.image_url && " · has image"}
            </p>
          </div>
        </div>
      ),
    },
    { header: "Difficulty", accessor: (q) => <Badge variant={q.difficulty === "hard" ? "danger" : q.difficulty === "medium" ? "warning" : "success"}>{q.difficulty ?? "—"}</Badge> },
    { header: "Marks", accessor: (q) => q.marks },
    { header: "Status", accessor: (q) => <Badge variant={q.is_active ? "success" : "neutral"} dot>{q.is_active ? "Active" : "Inactive"}</Badge> },
  ];

  return (
    <div>
      <PageHeader
        title="Questions"
        description="Create reusable objective questions for quizzes and exams."
        actions={
          <Button onClick={() => show()}>
            <Plus className="size-4" /> New Question
          </Button>
        }
      />
      <DataTable
        columns={cols}
        data={questions}
        keyExtractor={(q) => q.id}
        loading={isLoading}
        emptyTitle="No questions yet"
        rowActions={(q) => (
          <>
            <button onClick={() => show(q)} className="rounded-lg p-2 text-slate-400 hover:text-white">
              <Pencil className="size-4" />
            </button>
            {q.is_active && (
              <button onClick={() => setDeactivating(q)} className="rounded-lg p-2 text-slate-400 hover:text-danger-500">
                <Power className="size-4" />
              </button>
            )}
          </>
        )}
      />

      <Modal open={open} onClose={() => setOpen(false)} title={editing ? "Edit Question" : "New Question"} size="lg">
        <form onSubmit={submit} className="space-y-4">
          <Textarea label="Question" required rows={3} value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} />

          <div className="grid gap-4 sm:grid-cols-3">
            <Select
              label="Type"
              value={form.question_type}
              onChange={(e) => changeType(e.target.value as QuestionType)}
              options={QUESTION_TYPE_OPTIONS}
            />
            <Select
              label="Topic"
              placeholder="No topic"
              value={form.topic_id ? String(form.topic_id) : ""}
              onChange={(e) => setForm({ ...form, topic_id: e.target.value ? Number(e.target.value) : null })}
              options={topics.map((t) => ({ value: String(t.id), label: t.name }))}
            />
            <Select
              label="Difficulty"
              value={form.difficulty ?? "easy"}
              onChange={(e) => setForm({ ...form, difficulty: e.target.value as "easy" | "medium" | "hard" })}
              options={DIFFICULTY_OPTIONS}
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              Image {form.question_type && "(optional — diagrams, figures, code screenshots)"}
            </label>
            {form.image_url ? (
              <div className="flex items-center gap-3">
                <img src={form.image_url} alt="Question" className="h-20 w-20 rounded-lg object-cover ring-1 ring-white/10" />
                <button type="button" onClick={() => setForm({ ...form, image_url: null })} className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-400 hover:text-danger-500">
                  <X className="size-3.5" /> Remove
                </button>
              </div>
            ) : (
              <label className="flex w-fit cursor-pointer items-center gap-2 rounded-lg border border-dashed border-white/15 px-3 py-2 text-sm text-slate-400 hover:border-brand-400 hover:text-brand-300">
                <ImagePlus className="size-4" /> {uploadingImage ? "Uploading…" : "Upload image"}
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="hidden"
                  disabled={uploadingImage}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) uploadImage.mutate(file);
                    e.target.value = "";
                  }}
                />
              </label>
            )}
          </div>

          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label className="text-sm font-medium text-slate-300">
                Options — {form.question_type === "multiple_choice" ? "check every correct answer" : "select the correct answer"}
              </label>
              {form.question_type !== "true_false" && (
                <button type="button" onClick={addOption} className="flex items-center gap-1 text-xs text-brand-300 hover:text-brand-200">
                  <Plus className="size-3.5" /> Add option
                </button>
              )}
            </div>
            <div className="space-y-2">
              {optionRows.map((row, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input
                    type={form.question_type === "multiple_choice" ? "checkbox" : "radio"}
                    name="correct-option"
                    checked={correctIndexes.includes(i)}
                    onChange={() => toggleCorrect(i)}
                    className="size-4 shrink-0 accent-brand-500"
                  />
                  <Input
                    value={row}
                    placeholder={`Option ${i + 1}`}
                    disabled={form.question_type === "true_false"}
                    onChange={(e) => updateOption(i, e.target.value)}
                    className="flex-1"
                  />
                  {form.question_type !== "true_false" && optionRows.length > 2 && (
                    <button type="button" onClick={() => removeOption(i)} className="shrink-0 rounded-lg p-2 text-slate-400 hover:text-danger-500">
                      <Trash2 className="size-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <Textarea label="Explanation (optional)" rows={2} value={form.explanation ?? ""} onChange={(e) => setForm({ ...form, explanation: e.target.value })} />

          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Marks" type="number" min={1} required value={form.marks} onChange={(e) => setForm({ ...form, marks: Number(e.target.value) || 1 })} />
            <Switch checked={form.is_active} onChange={(is_active) => setForm({ ...form, is_active })} label="Active" />
          </div>

          <div className="flex gap-3">
            <Button type="button" variant="glass" className="flex-1" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" className="flex-1" loading={save.isPending}>
              Save
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!deactivating}
        onClose={() => setDeactivating(null)}
        onConfirm={() => deactivating && deactivate.mutate(deactivating.id)}
        title="Deactivate this question?"
        description="Past records stay intact."
        confirmLabel="Deactivate"
        loading={deactivate.isPending}
      />
    </div>
  );
}
