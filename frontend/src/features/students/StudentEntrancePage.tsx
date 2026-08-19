import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Calendar, FileSpreadsheet, Info, PlayCircle, Plus } from "lucide-react";
import { registrationsApi } from "@/api/studentEntrance";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardTitle } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { formatDateTime } from "@/lib/utils";

export function StudentEntrancePage() {
  const navigate = useNavigate();
  const { data: registrations = [], isLoading } = useQuery({ queryKey: ["my-entrance-registrations"], queryFn: registrationsApi.myRegistrations });

  return (
    <div>
      <PageHeader
        title="Entrance Exam"
        description="Your entrance-exam applications and invitation status."
        actions={<Button onClick={() => navigate("/entrance/apply")}><Plus className="size-4" /> Apply for an Exam</Button>}
      />
      <div className="mb-6 flex gap-3 rounded-xl border border-brand-500/20 bg-brand-500/5 p-4 text-sm text-brand-200">
        <Info className="size-5 shrink-0" />
        Apply, pick a slot, and pay your fee here. Once your college confirms your application, you can take the exam from this page.
      </div>
      {isLoading ? (
        <p className="text-slate-400">Loading applications…</p>
      ) : registrations.length === 0 ? (
        <Card>
          <CardTitle>No application yet</CardTitle>
          <p className="mt-2 text-sm text-slate-400">Use &ldquo;Apply for an Exam&rdquo; above to get started.</p>
        </Card>
      ) : (
        <div className="grid gap-4">
          {registrations.map((r) => (
            <Card key={r.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex size-10 items-center justify-center rounded-xl bg-brand-500/15 text-brand-300"><FileSpreadsheet className="size-5" /></div>
                  <div>
                    <CardTitle>{r.exam_name ?? `Exam #${r.exam_id}`}</CardTitle>
                    <p className="mt-1 text-xs text-slate-500">{r.registration_number ?? `Application #${r.id}`}</p>
                  </div>
                </div>
                <Badge variant={r.status === "confirmed" ? "success" : r.status === "pending_payment" ? "warning" : "neutral"} dot>{r.status.replaceAll("_", " ")}</Badge>
              </div>
              <p className="mt-4 flex items-center gap-2 text-sm text-slate-400"><Calendar className="size-4" />Applied {formatDateTime(r.registered_at)}</p>
              {r.status === "confirmed" && (
                <Button className="mt-4" onClick={() => navigate(`/entrance/exams/${r.exam_id}/take`)}>
                  <PlayCircle className="size-4" /> Take Exam
                </Button>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
