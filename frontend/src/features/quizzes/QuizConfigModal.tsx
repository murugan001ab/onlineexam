import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import { quizzesApi } from "@/api/quizzes";
import { questionsApi } from "@/api/questions";
import { classesApi } from "@/api/organization";
import { apiErrorMessage } from "@/api/client";
import type { QuizOut } from "@/types/quiz";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";

export function QuizConfigModal({ quiz, open, onClose }: { quiz: QuizOut; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [questionId, setQuestionId] = useState(""); const [classId, setClassId] = useState(""); const [marks, setMarks] = useState("");
  const { data: questions = [] } = useQuery({ queryKey: ["quiz-questions", quiz.id], queryFn: () => quizzesApi.listQuestions(quiz.id), enabled: open });
  const { data: availableQuestions = [] } = useQuery({ queryKey: ["questions"], queryFn: () => questionsApi.list(), enabled: open });
  const { data: classes = [] } = useQuery({ queryKey: ["classes"], queryFn: () => classesApi.list(), enabled: open });
  const { data: targets = [] } = useQuery({ queryKey: ["quiz-targets", quiz.id], queryFn: () => quizzesApi.listClassTargets(quiz.id), enabled: open });
  const refresh = () => { qc.invalidateQueries({ queryKey: ["quiz-questions", quiz.id] }); qc.invalidateQueries({ queryKey: ["quiz-targets", quiz.id] }); qc.invalidateQueries({ queryKey: ["quizzes"] }); };
  const addQuestion = useMutation({ mutationFn: () => quizzesApi.addQuestion(quiz.id, { question_id: Number(questionId), marks: marks ? Number(marks) : null, order_index: questions.length + 1 }), onSuccess: () => { toast.success("Question added"); setQuestionId(""); setMarks(""); refresh(); }, onError: (e) => toast.error(apiErrorMessage(e, "Could not add question")) });
  const removeQuestion = useMutation({ mutationFn: (id: number) => quizzesApi.removeQuestion(quiz.id, id), onSuccess: refresh, onError: (e) => toast.error(apiErrorMessage(e, "Could not remove question")) });
  const addClass = useMutation({ mutationFn: () => quizzesApi.assignClassTarget(quiz.id, { class_id: Number(classId) }), onSuccess: () => { toast.success("Class assigned"); setClassId(""); refresh(); }, onError: (e) => toast.error(apiErrorMessage(e, "Could not assign class")) });
  const removeClass = useMutation({ mutationFn: (id: number) => quizzesApi.unassignClassTarget(quiz.id, id), onSuccess: refresh, onError: (e) => toast.error(apiErrorMessage(e, "Could not remove class")) });
  const assignedQuestions = new Set(questions.map((q) => q.question_id)); const assignedClasses = new Set(targets.map((t) => t.class_id));
  return <Modal open={open} onClose={onClose} title={`Configure ${quiz.name}`} description="Choose questions and, for class quizzes, the target classes." size="lg"><div className="space-y-7"><section><h3 className="mb-3 font-medium text-white">Questions</h3><div className="mb-3 grid gap-2 sm:grid-cols-[1fr_120px_auto]"><Select placeholder="Select question" value={questionId} onChange={(e) => setQuestionId(e.target.value)} options={availableQuestions.filter((q) => !assignedQuestions.has(q.id)).map((q) => ({ value: String(q.id), label: q.text }))} /><Input type="number" min={1} placeholder="Marks" value={marks} onChange={(e) => setMarks(e.target.value)} /><Button disabled={!questionId || addQuestion.isPending} onClick={() => addQuestion.mutate()}><Plus className="size-4" /> Add</Button></div>
  <div className="space-y-2">{questions.map((q) => <div key={q.id} className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div><p className="text-sm text-slate-200">{q.text}</p><p className="text-xs text-slate-500">{q.question_type?.replaceAll("_", " ")} · {q.marks ?? "default"} marks</p></div><button onClick={() => removeQuestion.mutate(q.id)} className="p-2 text-slate-400 hover:text-danger-500"><Trash2 className="size-4" /></button></div>)}{questions.length === 0 && <p className="text-sm text-slate-500">No questions assigned.</p>}</div></section>
  {quiz.quiz_type === "class" && <section><h3 className="mb-3 font-medium text-white">Class targets</h3><div className="mb-3 flex gap-2"><Select className="flex-1" placeholder="Select class" value={classId} onChange={(e) => setClassId(e.target.value)} options={classes.filter((c) => !assignedClasses.has(c.id)).map((c) => ({ value: String(c.id), label: c.name }))} /><Button disabled={!classId || addClass.isPending} onClick={() => addClass.mutate()}><Plus className="size-4" /> Assign</Button></div><div className="flex flex-wrap gap-2">{targets.map((t) => <Badge key={t.id} variant="brand">{t.class_name}<button onClick={() => removeClass.mutate(t.id)} className="ml-2 text-brand-200 hover:text-danger-400">×</button></Badge>)}{targets.length === 0 && <p className="text-sm text-slate-500">Not assigned to any class.</p>}</div></section>}</div></Modal>;
}
