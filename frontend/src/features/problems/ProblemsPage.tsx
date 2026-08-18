import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Code2, Plus, Pencil, Power } from "lucide-react";
import toast from "react-hot-toast";
import { problemsApi } from "@/api/problems";
import { topicsApi } from "@/api/topics";
import { apiErrorMessage } from "@/api/client";
import type { Difficulty, ProblemCreate, ProblemListItem, ProblemOut } from "@/types/problem";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Badge, type BadgeProps } from "@/components/ui/Badge";

const DIFFICULTY_VARIANT: Record<string, BadgeProps["variant"]> = {
  easy: "success",
  medium: "warning",
  hard: "danger",
};

const DIFFICULTY_OPTIONS: { value: Difficulty; label: string }[] = [
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
];

const LANGUAGE_OPTIONS = ["python", "javascript", "java", "cpp", "c"];

const emptyForm: ProblemCreate = {
  title: "",
  slug: "",
  description: "",
  constraints: "",
  difficulty: "easy",
  time_limit_ms: 2000,
  memory_limit_kb: 65536,
  allowed_languages: ["python"],
  default_language: "python",
  is_active: true,
  topic_ids: [],
};

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export function ProblemsPage() {
  const queryClient = useQueryClient();
  const { data: problems = [], isLoading } = useQuery({
    queryKey: ["problems", { is_active: undefined }],
    queryFn: () => problemsApi.list({ is_active: undefined }),
  });
  const { data: topics = [] } = useQuery({ queryKey: ["topics"], queryFn: () => topicsApi.list() });

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ProblemListItem | null>(null);
  const [form, setForm] = useState<ProblemCreate>(emptyForm);
  const [slugTouched, setSlugTouched] = useState(false);
  const [toggling, setToggling] = useState<ProblemListItem | null>(null);
  const [loadingEdit, setLoadingEdit] = useState(false);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setSlugTouched(false);
    setModalOpen(true);
  }

  async function openEdit(item: ProblemListItem) {
    setLoadingEdit(true);
    try {
      const full: ProblemOut = await problemsApi.get(item.id);
      setEditing(item);
      setForm({
        title: full.title,
        slug: full.slug,
        description: full.description ?? "",
        constraints: full.constraints ?? "",
        starter_code: full.starter_code ?? "",
        difficulty: (full.difficulty as Difficulty) ?? "easy",
        time_limit_ms: full.time_limit_ms ?? 2000,
        memory_limit_kb: full.memory_limit_kb ?? 65536,
        allowed_languages: full.allowed_languages ?? ["python"],
        default_language: full.default_language ?? "python",
        is_active: full.is_active,
        topic_ids: full.topics.map((t) => t.id),
      });
      setSlugTouched(true);
      setModalOpen(true);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Could not load problem"));
    } finally {
      setLoadingEdit(false);
    }
  }

  const saveMutation = useMutation({
    mutationFn: (payload: ProblemCreate) =>
      editing ? problemsApi.update(editing.id, payload) : problemsApi.create(payload),
    onSuccess: () => {
      toast.success(editing ? "Problem updated" : "Problem created");
      queryClient.invalidateQueries({ queryKey: ["problems"] });
      setModalOpen(false);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not save problem")),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: number) => problemsApi.deactivate(id),
    onSuccess: () => {
      toast.success("Problem deactivated");
      queryClient.invalidateQueries({ queryKey: ["problems"] });
      setToggling(null);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not deactivate problem")),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    saveMutation.mutate(form);
  }

  function toggleLanguage(lang: string) {
    setForm((f) => {
      const current = f.allowed_languages ?? [];
      const next = current.includes(lang) ? current.filter((l) => l !== lang) : [...current, lang];
      return { ...f, allowed_languages: next };
    });
  }

  function toggleTopic(id: number) {
    setForm((f) => {
      const next = f.topic_ids.includes(id) ? f.topic_ids.filter((t) => t !== id) : [...f.topic_ids, id];
      return { ...f, topic_ids: next };
    });
  }

  const columns: Column<ProblemListItem>[] = [
    {
      header: "Problem",
      accessor: (p) => (
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500/20 to-accent-500/20 text-brand-300 ring-1 ring-inset ring-brand-500/20">
            <Code2 className="size-4" />
          </div>
          <div>
            <p className="font-medium text-slate-100">{p.title}</p>
            <p className="text-xs text-slate-500">{p.slug}</p>
          </div>
        </div>
      ),
    },
    {
      header: "Difficulty",
      accessor: (p) =>
        p.difficulty ? (
          <Badge variant={DIFFICULTY_VARIANT[p.difficulty] ?? "neutral"}>{p.difficulty}</Badge>
        ) : (
          <span className="text-slate-600">&mdash;</span>
        ),
    },
    {
      header: "Status",
      accessor: (p) => (
        <Badge variant={p.is_active ? "success" : "neutral"} dot>
          {p.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Problems"
        description="Coding-practice problems, difficulty, and topic tags."
        actions={
          <Button onClick={openCreate}>
            <Plus className="size-4" /> New Problem
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={problems}
        keyExtractor={(p) => p.id}
        loading={isLoading}
        emptyTitle="No problems yet"
        emptyDescription="Create your first coding problem to get started."
        rowActions={(p) => (
          <>
            <button
              onClick={() => openEdit(p)}
              disabled={loadingEdit}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white disabled:opacity-50"
            >
              <Pencil className="size-4" />
            </button>
            {p.is_active && (
              <button
                onClick={() => setToggling(p)}
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
        title={editing ? "Edit Problem" : "New Problem"}
        size="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input
              label="Title"
              required
              value={form.title}
              onChange={(e) => {
                const title = e.target.value;
                setForm((f) => ({ ...f, title, slug: slugTouched ? f.slug : slugify(title) }));
              }}
            />
            <Input
              label="Slug"
              required
              value={form.slug}
              onChange={(e) => {
                setSlugTouched(true);
                setForm({ ...form, slug: e.target.value });
              }}
            />
          </div>
          <Textarea
            label="Description"
            rows={4}
            value={form.description ?? ""}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <Textarea
            label="Constraints"
            rows={2}
            value={form.constraints ?? ""}
            onChange={(e) => setForm({ ...form, constraints: e.target.value })}
          />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Select
              label="Difficulty"
              value={form.difficulty ?? "easy"}
              onChange={(e) => setForm({ ...form, difficulty: e.target.value as Difficulty })}
              options={DIFFICULTY_OPTIONS}
            />
            <Input
              label="Time limit (ms)"
              type="number"
              min={1}
              value={form.time_limit_ms ?? ""}
              onChange={(e) => setForm({ ...form, time_limit_ms: Number(e.target.value) || undefined })}
            />
            <Input
              label="Memory limit (KB)"
              type="number"
              min={1}
              value={form.memory_limit_kb ?? ""}
              onChange={(e) => setForm({ ...form, memory_limit_kb: Number(e.target.value) || undefined })}
            />
          </div>

          <div>
            <p className="mb-1.5 text-sm font-medium text-slate-300">Allowed languages</p>
            <div className="flex flex-wrap gap-2">
              {LANGUAGE_OPTIONS.map((lang) => {
                const active = (form.allowed_languages ?? []).includes(lang);
                return (
                  <button
                    key={lang}
                    type="button"
                    onClick={() => toggleLanguage(lang)}
                    className={
                      active
                        ? "rounded-full bg-brand-500/20 px-3 py-1.5 text-xs font-medium text-brand-300 ring-1 ring-inset ring-brand-500/40"
                        : "rounded-full bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-slate-400 ring-1 ring-inset ring-white/10 hover:bg-white/[0.08]"
                    }
                  >
                    {lang}
                  </button>
                );
              })}
            </div>
          </div>

          {(form.allowed_languages?.length ?? 0) > 0 && (
            <Select
              label="Default language"
              value={form.default_language ?? form.allowed_languages![0]}
              onChange={(e) => setForm({ ...form, default_language: e.target.value })}
              options={(form.allowed_languages ?? []).map((l) => ({ value: l, label: l }))}
            />
          )}

          <div>
            <p className="mb-1.5 text-sm font-medium text-slate-300">Topics</p>
            <div className="flex flex-wrap gap-2">
              {topics.length === 0 && <p className="text-xs text-slate-600">No topics yet.</p>}
              {topics.map((t) => {
                const active = form.topic_ids.includes(t.id);
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => toggleTopic(t.id)}
                    className={
                      active
                        ? "rounded-full bg-accent-500/20 px-3 py-1.5 text-xs font-medium text-accent-300 ring-1 ring-inset ring-accent-500/40"
                        : "rounded-full bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-slate-400 ring-1 ring-inset ring-white/10 hover:bg-white/[0.08]"
                    }
                  >
                    {t.name}
                  </button>
                );
              })}
            </div>
          </div>

          <Switch
            checked={form.is_active}
            onChange={(checked) => setForm({ ...form, is_active: checked })}
            label="Active"
          />

          <div className="flex gap-3 pt-2">
            <Button type="button" variant="glass" className="flex-1" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" className="flex-1" loading={saveMutation.isPending}>
              {editing ? "Save Changes" : "Create Problem"}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!toggling}
        onClose={() => setToggling(null)}
        onConfirm={() => toggling && deactivateMutation.mutate(toggling.id)}
        title={`Deactivate ${toggling?.title}?`}
        description="This is a soft delete — the problem can be reactivated later by editing it."
        confirmLabel="Deactivate"
        loading={deactivateMutation.isPending}
      />
    </div>
  );
}
