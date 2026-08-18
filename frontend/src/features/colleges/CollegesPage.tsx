import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Mail, Phone, Plus, Pencil, Power, MapPin } from "lucide-react";
import toast from "react-hot-toast";
import { collegesApi } from "@/api/colleges";
import { apiErrorMessage } from "@/api/client";
import type { CollegeCreate, CollegeOut } from "@/types/college";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Badge } from "@/components/ui/Badge";

const emptyForm: CollegeCreate = {
  name: "",
  code: "",
  city: "",
  state: "",
  phone: "",
  email: "",
  address: "",
  pincode: "",
};

export function CollegesPage() {
  const queryClient = useQueryClient();
  const { data: colleges = [], isLoading } = useQuery({
    queryKey: ["colleges"],
    queryFn: () => collegesApi.list(),
  });

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<CollegeOut | null>(null);
  const [form, setForm] = useState<CollegeCreate>(emptyForm);
  const [deactivating, setDeactivating] = useState<CollegeOut | null>(null);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  }

  function openEdit(college: CollegeOut) {
    setEditing(college);
    setForm({
      name: college.name,
      code: college.code,
      city: college.city ?? "",
      state: college.state ?? "",
      phone: college.phone ?? "",
      email: college.email ?? "",
      address: college.address ?? "",
      pincode: college.pincode ?? "",
    });
    setModalOpen(true);
  }

  const saveMutation = useMutation({
    mutationFn: (payload: CollegeCreate) =>
      editing ? collegesApi.update(editing.id, payload) : collegesApi.create(payload),
    onSuccess: () => {
      toast.success(editing ? "College updated" : "College created");
      queryClient.invalidateQueries({ queryKey: ["colleges"] });
      setModalOpen(false);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not save college")),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: number) => collegesApi.deactivate(id),
    onSuccess: () => {
      toast.success("College deactivated");
      queryClient.invalidateQueries({ queryKey: ["colleges"] });
      setDeactivating(null);
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not deactivate college")),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    saveMutation.mutate(form);
  }

  const columns: Column<CollegeOut>[] = [
    {
      header: "College",
      accessor: (c) => (
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500/20 to-accent-500/20 text-brand-300 ring-1 ring-inset ring-brand-500/20">
            <Building2 className="size-4" />
          </div>
          <div>
            <p className="font-medium text-slate-100">{c.name}</p>
            <p className="text-xs text-slate-500">{c.code}</p>
          </div>
        </div>
      ),
    },
    {
      header: "Location",
      accessor: (c) =>
        c.city || c.state ? (
          <span className="flex items-center gap-1.5 text-sm">
            <MapPin className="size-3.5 text-slate-500" />
            {[c.city, c.state].filter(Boolean).join(", ")}
          </span>
        ) : (
          <span className="text-slate-600">&mdash;</span>
        ),
    },
    {
      header: "Contact",
      accessor: (c) => (
        <div className="space-y-1 text-xs">
          {c.email && (
            <p className="flex items-center gap-1.5">
              <Mail className="size-3 text-slate-500" /> {c.email}
            </p>
          )}
          {c.phone && (
            <p className="flex items-center gap-1.5">
              <Phone className="size-3 text-slate-500" /> {c.phone}
            </p>
          )}
          {!c.email && !c.phone && <span className="text-slate-600">&mdash;</span>}
        </div>
      ),
    },
    {
      header: "Status",
      accessor: (c) => (
        <Badge variant={c.is_active ? "success" : "neutral"} dot>
          {c.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Colleges"
        description="Manage every institution on the platform."
        actions={
          <Button onClick={openCreate}>
            <Plus className="size-4" /> New College
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={colleges}
        keyExtractor={(c) => c.id}
        loading={isLoading}
        emptyTitle="No colleges yet"
        emptyDescription="Create your first college to get started."
        rowActions={(c) => (
          <>
            <button
              onClick={() => openEdit(c)}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <Pencil className="size-4" />
            </button>
            {c.is_active && (
              <button
                onClick={() => setDeactivating(c)}
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
        title={editing ? "Edit College" : "New College"}
        description={editing ? `Editing ${editing.name}` : "Add a new institution to the platform."}
        size="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input
              label="College name"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <Input
              label="College code"
              required
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
            />
            <Input
              label="City"
              value={form.city ?? ""}
              onChange={(e) => setForm({ ...form, city: e.target.value })}
            />
            <Input
              label="State"
              value={form.state ?? ""}
              onChange={(e) => setForm({ ...form, state: e.target.value })}
            />
            <Input
              label="Pincode"
              value={form.pincode ?? ""}
              onChange={(e) => setForm({ ...form, pincode: e.target.value })}
            />
            <Input
              label="Phone"
              value={form.phone ?? ""}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
            <Input
              label="Email"
              type="email"
              value={form.email ?? ""}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
            <Input
              label="Address"
              value={form.address ?? ""}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
          </div>
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="glass" className="flex-1" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" className="flex-1" loading={saveMutation.isPending}>
              {editing ? "Save Changes" : "Create College"}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!deactivating}
        onClose={() => setDeactivating(null)}
        onConfirm={() => deactivating && deactivateMutation.mutate(deactivating.id)}
        title={`Deactivate ${deactivating?.name}?`}
        description="This is a soft delete — the college can be reactivated later, but staff and students there will lose access."
        confirmLabel="Deactivate"
        loading={deactivateMutation.isPending}
      />
    </div>
  );
}
