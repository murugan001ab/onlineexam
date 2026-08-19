import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { Lock, ArrowRight, GraduationCap } from "lucide-react";
import { redeemInvitation } from "@/api/auth";
import { apiErrorMessage } from "@/api/client";
import { useAuthStore } from "@/store/authStore";
import { AuroraBackground } from "@/components/ui/AuroraBackground";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export function RedeemInvitationPage() {
  const [params] = useSearchParams(); const navigate = useNavigate(); const [password, setPassword] = useState(""); const [confirm, setConfirm] = useState(""); const [loading, setLoading] = useState(false);
  async function submit(e: FormEvent) { e.preventDefault(); const token = params.get("token"); if (!token) return toast.error("This invitation link is missing its token."); if (password.length < 8 || password !== confirm) return toast.error("Passwords must match and contain at least 8 characters."); setLoading(true); try { const user = await redeemInvitation(token, password); useAuthStore.setState({ user, status: "authenticated", error: null }); toast.success("Invitation accepted. Welcome!"); navigate("/dashboard", { replace: true }); } catch (err) { toast.error(apiErrorMessage(err, "This invitation is invalid or expired.")); } finally { setLoading(false); } }
  return <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4"><AuroraBackground /><div className="glass-panel relative w-full max-w-md p-8"><div className="mb-6 flex items-center gap-3"><div className="flex size-11 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500"><GraduationCap className="size-6 text-white" /></div><div><h1 className="font-display text-xl font-bold text-white">Exam invitation</h1><p className="text-sm text-slate-400">Set your student password</p></div></div><form onSubmit={submit} className="space-y-4"><Input label="New password" type="password" icon={<Lock className="size-4" />} required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} /><Input label="Confirm password" type="password" icon={<Lock className="size-4" />} required minLength={8} value={confirm} onChange={(e) => setConfirm(e.target.value)} /><Button type="submit" className="w-full" loading={loading}>Accept invitation <ArrowRight className="size-4" /></Button></form></div></div>;
}
