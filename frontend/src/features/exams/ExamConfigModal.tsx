import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Plus, Trash2, Copy, QrCode, CalendarClock } from "lucide-react";
import toast from "react-hot-toast";
import { examsApi } from "@/api/exams";
import { quizzesApi } from "@/api/quizzes";
import { problemsApi } from "@/api/problems";
import { topicsApi } from "@/api/topics";
import { apiErrorMessage } from "@/api/client";
import type { ExamOut } from "@/types/exam";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";

export function ExamConfigModal({ exam, open, onClose }: { exam: ExamOut; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();

  const [quizId, setQuizId] = useState("");
  const [topicId, setTopicId] = useState("");
  const [count, setCount] = useState("");
  const [weight, setWeight] = useState("");
  const [problemId, setProblemId] = useState("");
  const [problemMarks, setProblemMarks] = useState("");

  const { data: linkedQuizzes = [] } = useQuery({
    queryKey: ["exam-quizzes", exam.id],
    queryFn: () => examsApi.listQuizzes(exam.id),
    enabled: open,
  });
  const { data: quizzes = [] } = useQuery({
    queryKey: ["quizzes"],
    queryFn: () => quizzesApi.list(),
    enabled: open,
  });
  const { data: weights = [] } = useQuery({
    queryKey: ["exam-weights", exam.id],
    queryFn: () => examsApi.listTopicWeights(exam.id),
    enabled: open,
  });
  const { data: topics = [] } = useQuery({
    queryKey: ["topics"],
    queryFn: topicsApi.list,
    enabled: open,
  });
  const { data: linkedProblems = [] } = useQuery({
    queryKey: ["exam-problems", exam.id],
    queryFn: () => examsApi.listProblems(exam.id),
    enabled: open,
  });
  const { data: problems = [] } = useQuery({
    queryKey: ["problems"],
    queryFn: () => problemsApi.list(),
    enabled: open,
  });

  function refresh() {
    qc.invalidateQueries({ queryKey: ["exam-quizzes", exam.id] });
    qc.invalidateQueries({ queryKey: ["exam-weights", exam.id] });
    qc.invalidateQueries({ queryKey: ["exam-problems", exam.id] });
  }

  function copyLink() {
    if (exam.public_url) {
      navigator.clipboard.writeText(exam.public_url);
      toast.success("Link copied");
    }
  }

  const addQuiz = useMutation({
    mutationFn: () => examsApi.assignQuiz(exam.id, { quiz_id: Number(quizId), order_index: linkedQuizzes.length + 1 }),
    onSuccess: () => {
      setQuizId("");
      refresh();
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not assign quiz")),
  });
  const removeQuiz = useMutation({
    mutationFn: (id: number) => examsApi.unassignQuiz(exam.id, id),
    onSuccess: refresh,
    onError: (e) => toast.error(apiErrorMessage(e, "Could not remove quiz")),
  });

  const addWeight = useMutation({
    mutationFn: () =>
      examsApi.addTopicWeight(exam.id, {
        topic_id: Number(topicId),
        question_count: Number(count),
        weight: weight ? Number(weight) : null,
      }),
    onSuccess: () => {
      setTopicId("");
      setCount("");
      setWeight("");
      refresh();
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not add topic weight")),
  });
  const removeWeight = useMutation({
    mutationFn: (id: number) => examsApi.removeTopicWeight(exam.id, id),
    onSuccess: refresh,
    onError: (e) => toast.error(apiErrorMessage(e, "Could not remove topic weight")),
  });

  const addProblem = useMutation({
    mutationFn: () =>
      examsApi.assignProblem(exam.id, {
        problem_id: Number(problemId),
        order_index: linkedProblems.length + 1,
        marks: problemMarks ? Number(problemMarks) : null,
      }),
    onSuccess: () => {
      setProblemId("");
      setProblemMarks("");
      refresh();
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not link problem")),
  });
  const removeProblem = useMutation({
    mutationFn: (id: number) => examsApi.unassignProblem(exam.id, id),
    onSuccess: refresh,
    onError: (e) => toast.error(apiErrorMessage(e, "Could not remove problem")),
  });

  const linkedQuizIds = new Set(linkedQuizzes.map((q) => q.quiz_id));
  const weightedTopicIds = new Set(weights.map((w) => w.topic_id));
  const linkedProblemIds = new Set(linkedProblems.map((p) => p.problem_id));

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Configure ${exam.name}`}
      description="Link prepared quizzes, coding problems, topic weights, and the public registration link."
      size="lg"
    >
      <div className="space-y-7">
        {exam.public_url && (
          <section className="flex items-center gap-4 rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=110x110&data=${encodeURIComponent(exam.public_url)}`}
              alt="QR code for exam link"
              className="size-[110px] rounded-lg bg-white p-1.5"
            />
            <div className="min-w-0 flex-1">
              <h3 className="flex items-center gap-2 font-medium text-white">
                <QrCode className="size-4 text-brand-300" /> Public registration link
              </h3>
              <p className="mt-1 truncate text-sm text-slate-400">{exam.public_url}</p>
              <p className="mt-1 text-xs text-slate-500">
                Share via WhatsApp, a poster, or your college portal — anyone with this link or QR can view
                the exam and register.
              </p>
              <Button type="button" variant="glass" className="mt-2" onClick={copyLink}>
                <Copy className="size-4" /> Copy link
              </Button>
            </div>
          </section>
        )}

        <section className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <div>
            <h3 className="flex items-center gap-2 font-medium text-white">
              <CalendarClock className="size-4 text-brand-300" /> Booking slots
            </h3>
            <p className="mt-1 text-sm text-slate-400">
              How many sittings run for this exam, and how many students each one holds.
            </p>
          </div>
          <Link to={`/exam-slots?exam=${exam.id}`}>
            <Button type="button" variant="glass">
              Manage slots
            </Button>
          </Link>
        </section>

        <section>
          <h3 className="mb-3 font-medium text-white">Quiz sequence</h3>
          <div className="mb-3 flex gap-2">
            <Select
              className="flex-1"
              placeholder="Select quiz"
              value={quizId}
              onChange={(e) => setQuizId(e.target.value)}
              options={quizzes.filter((q) => !linkedQuizIds.has(q.id)).map((q) => ({ value: String(q.id), label: q.name }))}
            />
            <Button disabled={!quizId || addQuiz.isPending} onClick={() => addQuiz.mutate()}>
              <Plus className="size-4" /> Add
            </Button>
          </div>
          <div className="space-y-2">
            {linkedQuizzes.map((q, index) => (
              <div key={q.id} className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
                <span className="text-sm text-slate-200">
                  {index + 1}. {q.quiz_name}
                </span>
                <button onClick={() => removeQuiz.mutate(q.id)} className="p-2 text-slate-400 hover:text-danger-500">
                  <Trash2 className="size-4" />
                </button>
              </div>
            ))}
            {linkedQuizzes.length === 0 && <p className="text-sm text-slate-500">No quizzes linked.</p>}
          </div>
        </section>

        <section>
          <h3 className="mb-3 font-medium text-white">Topic weightage</h3>
          <div className="mb-3 grid gap-2 sm:grid-cols-[1fr_100px_100px_auto]">
            <Select
              placeholder="Select topic"
              value={topicId}
              onChange={(e) => setTopicId(e.target.value)}
              options={topics.filter((t) => !weightedTopicIds.has(t.id)).map((t) => ({ value: String(t.id), label: t.name }))}
            />
            <Input type="number" min={1} placeholder="Questions" value={count} onChange={(e) => setCount(e.target.value)} />
            <Input type="number" min={0} step="0.01" placeholder="Weight" value={weight} onChange={(e) => setWeight(e.target.value)} />
            <Button disabled={!topicId || !count || addWeight.isPending} onClick={() => addWeight.mutate()}>
              <Plus className="size-4" /> Add
            </Button>
          </div>
          <div className="space-y-2">
            {weights.map((w) => (
              <div key={w.id} className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
                <span className="text-sm text-slate-200">
                  {w.topic_name}{" "}
                  <span className="text-slate-500">
                    · {w.question_count} questions{w.weight != null ? ` · weight ${w.weight}` : ""}
                  </span>
                </span>
                <button onClick={() => removeWeight.mutate(w.id)} className="p-2 text-slate-400 hover:text-danger-500">
                  <Trash2 className="size-4" />
                </button>
              </div>
            ))}
            {weights.length === 0 && <p className="text-sm text-slate-500">No topic weights set.</p>}
          </div>
        </section>

        <section>
          <h3 className="mb-3 font-medium text-white">Coding problems</h3>
          <div className="mb-3 grid gap-2 sm:grid-cols-[1fr_100px_auto]">
            <Select
              placeholder="Select problem"
              value={problemId}
              onChange={(e) => setProblemId(e.target.value)}
              options={problems.filter((p) => !linkedProblemIds.has(p.id)).map((p) => ({ value: String(p.id), label: p.title }))}
            />
            <Input type="number" min={0} placeholder="Marks" value={problemMarks} onChange={(e) => setProblemMarks(e.target.value)} />
            <Button disabled={!problemId || addProblem.isPending} onClick={() => addProblem.mutate()}>
              <Plus className="size-4" /> Add
            </Button>
          </div>
          <div className="space-y-2">
            {linkedProblems.map((p, index) => (
              <div key={p.id} className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
                <span className="text-sm text-slate-200">
                  {index + 1}. {p.problem_title} <span className="text-slate-500">{p.marks != null ? `· ${p.marks} marks` : ""}</span>
                </span>
                <button onClick={() => removeProblem.mutate(p.id)} className="p-2 text-slate-400 hover:text-danger-500">
                  <Trash2 className="size-4" />
                </button>
              </div>
            ))}
            {linkedProblems.length === 0 && (
              <p className="text-sm text-slate-500">No coding problems linked — this exam is objective-only.</p>
            )}
          </div>
        </section>
      </div>
    </Modal>
  );
}
