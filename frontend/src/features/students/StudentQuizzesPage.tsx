import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ListChecks, PlayCircle, CheckCircle2 } from "lucide-react";
import { classQuizAttemptsApi } from "@/api/classQuizAttempts";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardTitle } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";

export function StudentQuizzesPage() {
  const navigate = useNavigate();
  const { data: quizzes = [], isLoading } = useQuery({ queryKey: ["student-quizzes"], queryFn: classQuizAttemptsApi.listAvailable });
  const isDone = (status: string | null) => status === "submitted" || status === "graded";

  return (
    <div>
      <PageHeader title="Class Quizzes" description="Quizzes assigned to your enrolled classes." />
      {isLoading ? (
        <p className="text-slate-400">Loading quizzes…</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {quizzes.map((q) => (
            <Card key={q.id}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <ListChecks className="size-5 text-brand-300" />
                  <div>
                    <CardTitle>{q.name}</CardTitle>
                    <p className="text-xs text-slate-500">{q.subject ?? q.class_name}</p>
                  </div>
                </div>
                <Badge variant={isDone(q.attempt_status) ? "success" : "brand"}>{q.attempt_status ?? "Ready"}</Badge>
              </div>
              <p className="mt-3 text-sm text-slate-400">{q.description ?? "Complete this quiz during its scheduled window."}</p>
              {q.duration_minutes && <p className="mt-3 text-xs text-slate-500">Duration: {q.duration_minutes} minutes</p>}
              <Button
                className="mt-4 w-full"
                variant={isDone(q.attempt_status) ? "glass" : "primary"}
                onClick={() => navigate(`/quizzes/${q.id}/take`)}
              >
                {isDone(q.attempt_status) ? (
                  <><CheckCircle2 className="size-4" /> View Result</>
                ) : q.attempt_status ? (
                  <><PlayCircle className="size-4" /> Continue</>
                ) : (
                  <><PlayCircle className="size-4" /> Start Quiz</>
                )}
              </Button>
            </Card>
          ))}
          {quizzes.length === 0 && (
            <Card><CardTitle>No quizzes assigned</CardTitle><p className="mt-2 text-sm text-slate-400">Your class quizzes will appear here.</p></Card>
          )}
        </div>
      )}
    </div>
  );
}
