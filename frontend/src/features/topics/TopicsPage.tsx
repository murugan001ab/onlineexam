import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Plus, Pencil, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import { topicsApi } from "@/api/topics";
import { apiErrorMessage } from "@/api/client";
import type { TopicCreate, TopicOut } from "@/types/topic";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Badge } from "@/components/ui/Badge";

const emptyForm: TopicCreate = { name: "", slug: "", parent_id: null, order_index: null };

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export function TopicsPage() {
  const queryClient = useQueryClient();
  const { data: topics = [], isLoading } = useQuery({
    queryKey: ["topics"],
    queryFn: () => topicsApi.list(),
  });
  const topicMap = new Map(topics.map((t) => [t.id, t.name]));

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<TopicOut | null>(null);
  const [form, setForm] = useState<TopicCreate>(emptyForm);
  const [slugTouched, setSlugTouched] = useState(false);
  const [deleting, setDeleting] = useState<TopicOut | null>(null);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setSlugTouched(false);
    setModalOpen(true);
  }

  function openEdit(topic: TopicOut) {
    setEditing(topic);
    setForm({
      name: topic.name,
      slug: topic.slug,
      parent_id: topic.parent_id,
      order_index: topic.order_index,
    });
    setSlugTouched(true);
    setModalOpen(true);
  }

  const saveMutation = useMutation({
    mutationFn: (payload: TopicCreate) =>
      editing ? topicsApi.update(editing.id, payload) : topicsApi.create(payload),
    onSuccess: () => {
      toast.success(editing ? "Topic updated" : "Topic created");
      queryClient.invalidateQueries({ queryKey: ["topics"] });
      setModalOpen(false);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not save topic")),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => topicsApi.remove(id),
    onSuccess: () => {
      toast.success("Topic deleted");
      queryClient.invalidateQueries({ queryKey: ["topics"] });
      setDeleting(null);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not delete topic")),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    saveMutation.mutate(form);
  }

  const columns: Column<TopicOut>[] = [
    {
      header: "Topic",
      accessor: (t) => (
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500/20 to-accent-500/20 text-brand-300 ring-1 ring-inset ring-brand-500/20">
            <BookOpen className="size-4" />
          </div>
          <div>
            <p className="font-medium text-slate-100">{t.name}</p>
            <p className="text-xs text-slate-500">{t.slug}</p>
          </div>
        </div>
      ),
    },
    {
      header: "Parent",
      accessor: (t) =>
        t.parent_id ? (
          <Badge variant="neutral">{topicMap.get(t.parent_id) ?? `#${t.parent_id}`}</Badge>
        ) : (
          <span className="text-slate-600">&mdash; root &mdash;</span>
        ),
    },
    {
      header: "Order",
      accessor: (t) => <span className="text-slate-400">{t.order_index ?? "\u2014"}</span>,
    },
  ];

  return (
    <div>
      <PageHeader
        title="Topics"
        description="Organize the subject hierarchy used by problems, questions, and exam weightage."
        actions={
          <Button onClick={openCreate}>
            <Plus className="size-4" /> New Topic
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={topics}
        keyExtractor={(t) => t.id}
        loading={isLoading}
        emptyTitle="No topics yet"
        emptyDescription="Create your first topic to start organizing content."
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

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit Topic" : "New Topic"}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Name"
            required
            value={form.name}
            onChange={(e) => {
              const name = e.target.value;
              setForm((f) => ({ ...f, name, slug: slugTouched ? f.slug : slugify(name) }));
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
          <Select
            label="Parent topic"
            placeholder="None (root topic)"
            value={form.parent_id ? String(form.parent_id) : ""}
            onChange={(e) => setForm({ ...form, parent_id: e.target.value ? Number(e.target.value) : null })}
            options={topics
              .filter((t) => t.id !== editing?.id)
              .map((t) => ({ value: String(t.id), label: t.name }))}
          />
          <Input
            label="Order index"
            type="number"
            value={form.order_index ?? ""}
            onChange={(e) =>
              setForm({ ...form, order_index: e.target.value === "" ? null : Number(e.target.value) })
            }
          />
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="glass" className="flex-1" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" className="flex-1" loading={saveMutation.isPending}>
              {editing ? "Save Changes" : "Create Topic"}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title={`Delete ${deleting?.name}?`}
        description="Topics still referenced by child topics, questions, problems, or exam weights can't be deleted."
        confirmLabel="Delete"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
