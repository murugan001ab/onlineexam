import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Eye, GraduationCap } from "lucide-react";
import { quizAttemptsAdminApi } from "@/api/classQuizAttempts";
import { quizzesApi } from "@/api/quizzes";
import type { AttemptOut } from "@/types/attempt";
import { Badge, type BadgeProps } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { PageHeader } from "@/components/ui/PageHeader";
import { formatDateTime } from "@/lib/utils";
import { QuizAttemptAnswersModal } from "./QuizAttemptAnswersModal";

const STATUS_VARIANT: Record<string, BadgeProps["variant"]> = {
  in_progress: "warning",
  submitted: "brand",
  graded: "success",
  expired: "danger",
};

export function QuizAttemptsPage() {
  const { quizId } = useParams<{ quizId: string }>();
  const navigate = useNavigate();
  const id = Number(quizId);
  const [reviewing, setReviewing] = useState<AttemptOut | null>(null);

  const { data: quiz } = useQuery({ queryKey: ["quiz", id], queryFn: () => quizzesApi.get(id), enabled: Number.isFinite(id) });
  const { data: attempts = [], isLoading } = useQuery({ queryKey: ["quiz-attempts", id], queryFn: () => quizAttemptsAdminApi.list(id), enabled: Number.isFinite(id) });

  const columns: Column<AttemptOut>[] = [
    {
      header: "Student",
      accessor: (a) => (
        <div className="flex items-center gap-3">
          <div className="flex size-8 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-accent-500"><GraduationCap className="size-4" /></div>
          <span className="text-slate-200">Student #{a.student_id}</span>
        </div>
      ),
    },
    { header: "Status", accessor: (a) => <Badge variant={STATUS_VARIANT[a.status] ?? "neutral"} dot>{a.status.replaceAll("_", " ")}</Badge> },
    { header: "Score", accessor: (a) => a.score !== null ? <span className="font-medium text-slate-100">{a.score} / {a.total_marks ?? "—"}</span> : <span className="text-slate-600">—</span> },
    { header: "Started", accessor: (a) => <span className="text-xs text-slate-400">{formatDateTime(a.started_at)}</span> },
    { header: "Submitted", accessor: (a) => <span className="text-xs text-slate-400">{formatDateTime(a.submitted_at)}</span> },
  ];

  return (
    <div>
      <button onClick={() => navigate("/quizzes")} className="mb-3 flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300">
        <ArrowLeft className="size-3.5" /> Back to Quizzes
      </button>
      <PageHeader title={quiz ? `Attempts — ${quiz.name}` : "Quiz Attempts"} description="Review who has attempted this quiz and how they scored." />
      <DataTable
        columns={columns}
        data={attempts}
        keyExtractor={(a) => a.id}
        loading={isLoading}
        emptyTitle="No attempts yet"
        emptyDescription="Once students start this quiz, their attempts will show up here."
        rowActions={(a) => (
          <Button size="sm" variant="glass" onClick={() => setReviewing(a)}>
            <Eye className="size-3.5" /> Review
          </Button>
        )}
      />
      {reviewing && <QuizAttemptAnswersModal quizId={id} attemptId={reviewing.id} onClose={() => setReviewing(null)} />}
    </div>
  );
}
