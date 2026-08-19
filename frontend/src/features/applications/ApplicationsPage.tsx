import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileText, Mail, RefreshCw, Send, Users } from "lucide-react";
import toast from "react-hot-toast";
import { examsApi } from "@/api/exams";
import { registrationsApi } from "@/api/registrations";
import { apiErrorMessage } from "@/api/client";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { formatDateTime } from "@/lib/utils";
import type { ExamRegistrationOut } from "@/types/registration";
import { DocumentReviewModal } from "@/features/applications/DocumentReviewModal";

export function ApplicationsPage() {
  const qc = useQueryClient();
  const [examId, setExamId] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [reviewingStudentId, setReviewingStudentId] = useState<number | null>(null);

  const { data: exams = [] } = useQuery({ queryKey: ["exams"], queryFn: () => examsApi.list() });
  const { data: applications = [], isLoading } = useQuery({
    queryKey: ["applications", examId],
    queryFn: () => registrationsApi.list(Number(examId)),
    enabled: !!examId,
  });
  const { data: invitations = [] } = useQuery({
    queryKey: ["invitations", examId],
    queryFn: () => registrationsApi.invitations(Number(examId)),
    enabled: !!examId,
  });

  const send = useMutation({
    mutationFn: () => registrationsApi.generateInvitations(Number(examId), selected.length ? selected : undefined),
    onSuccess: (rows) => {
      toast.success(`${rows.length} invitation(s) generated and emailed`);
      setSelected([]);
      qc.invalidateQueries({ queryKey: ["invitations", examId] });
      qc.invalidateQueries({ queryKey: ["applications", examId] });
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not send invitations")),
  });
  const resend = useMutation({
    mutationFn: registrationsApi.resendInvitation,
    onSuccess: () => {
      toast.success("Invitation resent");
      qc.invalidateQueries({ queryKey: ["invitations", examId] });
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not resend invitation")),
  });

  const invited = new Set(invitations.map((i) => i.registration_id));
  const confirmed = applications.filter((a) => a.status === "confirmed");
  const selectable = confirmed.filter((a) => !invited.has(a.id));
  const allSelected = selectable.length > 0 && selectable.every((a) => selected.includes(a.id));

  const cols: Column<ExamRegistrationOut>[] = [
    {
      header: "Application",
      accessor: (a) => (
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500/20 to-accent-500/20 text-brand-300">
            <Users className="size-4" />
          </div>
          <div>
            <p className="font-medium text-slate-100">Student #{a.student_id}</p>
            <p className="text-xs text-slate-500">{a.registration_number ?? `Application #${a.id}`}</p>
          </div>
        </div>
      ),
    },
    { header: "Slot", accessor: (a) => (a.slot_id ? `Slot #${a.slot_id}` : "—") },
    {
      header: "Applied",
      accessor: (a) => <span className="text-xs text-slate-400">{formatDateTime(a.registered_at)}</span>,
    },
    {
      header: "Status",
      accessor: (a) => (
        <Badge variant={a.status === "confirmed" ? "success" : a.status === "pending_payment" ? "warning" : "neutral"} dot>
          {a.status.replaceAll("_", " ")}
        </Badge>
      ),
    },
    {
      header: "Invitation",
      accessor: (a) =>
        invited.has(a.id) ? (
          <Badge variant="brand">
            <Mail className="mr-1 size-3" /> Sent
          </Badge>
        ) : (
          <span className="text-xs text-slate-500">Not sent</span>
        ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Applied Students"
        description="Review paid applications and send exam invitations when you approve them."
        actions={
          <Button disabled={!examId || !selectable.length || send.isPending} onClick={() => send.mutate()}>
            <Send className="size-4" /> Send Selected / All
          </Button>
        }
      />

      <div className="mb-5 flex flex-wrap items-end gap-3">
        <Select
          label="Entrance exam"
          className="max-w-md"
          placeholder="Select an exam"
          value={examId}
          onChange={(e) => {
            setExamId(e.target.value);
            setSelected([]);
          }}
          options={exams.map((e) => ({ value: String(e.id), label: e.name }))}
        />
        <Button variant="glass" disabled={!examId} onClick={() => qc.invalidateQueries({ queryKey: ["applications", examId] })}>
          <RefreshCw className="size-4" />
        </Button>
      </div>

      {examId && (
        <div className="mb-3 flex items-center justify-between rounded-xl border border-brand-500/20 bg-brand-500/5 px-4 py-3 text-sm text-brand-200">
          <span>
            <CheckCircle2 className="mr-2 inline size-4" />
            {confirmed.length} confirmed application(s), {selectable.length} awaiting invitation
          </span>
          <button
            className="text-xs underline"
            onClick={() => setSelected(allSelected ? [] : selectable.map((a) => a.id))}
          >
            {allSelected ? "Clear selection" : "Select all"}
          </button>
        </div>
      )}

      <DataTable
        columns={cols}
        data={applications}
        keyExtractor={(a) => a.id}
        loading={!!examId && isLoading}
        emptyTitle={examId ? "No applications" : "Select an exam"}
        rowActions={(a) => (
          <>
            <button
              onClick={() => setReviewingStudentId(a.student_id)}
              title="Review documents"
              className="rounded-lg p-2 text-slate-400 hover:text-brand-300"
            >
              <FileText className="size-4" />
            </button>
            {a.status === "confirmed" && !invited.has(a.id) && (
              <input
                type="checkbox"
                checked={selected.includes(a.id)}
                onChange={() =>
                  setSelected((s) => (s.includes(a.id) ? s.filter((id) => id !== a.id) : [...s, a.id]))
                }
                className="size-4 accent-brand-500"
              />
            )}
            {invited.has(a.id) && (
              <button
                onClick={() => {
                  const invitation = invitations.find((i) => i.registration_id === a.id);
                  if (invitation) resend.mutate(invitation.id);
                }}
                title="Resend invitation"
                className="rounded-lg p-2 text-slate-400 hover:text-brand-300"
              >
                <Mail className="size-4" />
              </button>
            )}
          </>
        )}
      />

      <DocumentReviewModal
        studentId={reviewingStudentId}
        open={reviewingStudentId != null}
        onClose={() => setReviewingStudentId(null)}
      />
    </div>
  );
}
