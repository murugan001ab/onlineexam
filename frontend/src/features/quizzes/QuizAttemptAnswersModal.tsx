import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle } from "lucide-react";
import { quizAttemptsAdminApi } from "@/api/classQuizAttempts";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { cn } from "@/lib/utils";

function optionEntries(options: Record<string, string> | string[] | null): [string, string][] {
  if (!options) return [];
  if (Array.isArray(options)) return options.map((label, i) => [String(i), label]);
  return Object.entries(options);
}

export function QuizAttemptAnswersModal({
  quizId,
  attemptId,
  onClose,
}: {
  quizId: number;
  attemptId: number;
  onClose: () => void;
}) {
  const { data: answers = [], isLoading } = useQuery({
    queryKey: ["quiz-attempt-answers", quizId, attemptId],
    queryFn: () => quizAttemptsAdminApi.reviewAnswers(quizId, attemptId),
  });

  return (
    <Modal open onClose={onClose} title="Attempt review" description="Answers submitted for this attempt." size="lg">
      {isLoading ? (
        <div className="flex justify-center py-10"><Spinner size={24} /></div>
      ) : (
        <div className="space-y-4">
          {answers.map((a, i) => (
            <div key={i} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <div className="mb-2 flex items-start justify-between gap-3">
                <p className="text-sm text-slate-100">{a.text}</p>
                {a.is_correct !== null && (
                  a.is_correct ? <CheckCircle2 className="size-4 shrink-0 text-emerald-400" /> : <XCircle className="size-4 shrink-0 text-danger-500" />
                )}
              </div>
              <div className="space-y-1.5">
                {optionEntries(a.options).map(([key, label]) => {
                  const isSelected = Array.isArray(a.selected_answer) ? a.selected_answer.includes(key) : a.selected_answer === key;
                  const isCorrect = Array.isArray(a.correct_answer) ? a.correct_answer.includes(key) : a.correct_answer === key;
                  return (
                    <p
                      key={key}
                      className={cn(
                        "rounded-lg px-3 py-1.5 text-xs",
                        isCorrect ? "bg-success-500/15 text-emerald-300" : isSelected ? "bg-danger-500/15 text-rose-300" : "text-slate-500",
                      )}
                    >
                      {label} {isSelected && "· selected"} {isCorrect && "· correct"}
                    </p>
                  );
                })}
              </div>
              <p className="mt-2 text-xs text-slate-500">{a.marks_awarded ?? 0} / {a.marks ?? "—"} marks</p>
            </div>
          ))}
          {answers.length === 0 && <p className="py-6 text-center text-sm text-slate-500">No answers recorded.</p>}
        </div>
      )}
    </Modal>
  );
}
