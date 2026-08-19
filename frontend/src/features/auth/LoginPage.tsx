import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { GraduationCap, Lock, User, ArrowRight, ShieldCheck, Sparkles } from "lucide-react";
import toast from "react-hot-toast";
import { useAuthStore } from "@/store/authStore";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { AuroraBackground } from "@/components/ui/AuroraBackground";
import { apiErrorMessage } from "@/api/client";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const login = useAuthStore((s) => s.login);
  const status = useAuthStore((s) => s.status);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ username?: string; password?: string }>({});

  const loading = status === "authenticating";

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errors: typeof fieldErrors = {};
    if (!username.trim()) errors.username = "Username is required";
    if (!password) errors.password = "Password is required";
    setFieldErrors(errors);
    if (Object.keys(errors).length) return;

    try {
      await login(username.trim(), password);
      toast.success("Welcome back!");
      const from = (location.state as { from?: string } | null)?.from ?? "/dashboard";
      navigate(from, { replace: true });
    } catch (err) {
      toast.error(apiErrorMessage(err, "Invalid username or password"));
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12">
      <AuroraBackground />

      <div className="grid w-full max-w-5xl grid-cols-1 overflow-hidden rounded-3xl border border-white/10 bg-white/[0.02] shadow-2xl shadow-black/40 backdrop-blur-2xl lg:grid-cols-2">
        {/* Left / branding panel */}
        <motion.div
          initial={{ opacity: 0, x: -24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-brand-600/90 via-brand-500/80 to-accent-500/80 p-10 lg:flex"
        >
          <div className="absolute inset-0 opacity-20" style={{
            backgroundImage: "radial-gradient(circle at 20% 20%, white 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }} />

          <div className="relative z-10 flex items-center gap-3">
            <div className="flex size-11 items-center justify-center rounded-2xl bg-white/15 backdrop-blur-md">
              <GraduationCap className="size-6 text-white" />
            </div>
            <span className="font-display text-xl font-bold text-white">ExamPortal</span>
          </div>

          <div className="relative z-10 space-y-6">
            <motion.div
              animate={{ y: [0, -12, 0] }}
              transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
              className="flex size-14 items-center justify-center rounded-2xl bg-white/15 backdrop-blur-md"
            >
              <Sparkles className="size-7 text-white" />
            </motion.div>
            <h1 className="font-display text-3xl font-bold leading-tight text-white">
              Assess. Analyze.
              <br />
              Accelerate learning.
            </h1>
            <p className="max-w-sm text-sm leading-relaxed text-white/80">
              A unified platform for coding assessments, MCQ quizzes, and entrance exams
              &mdash; built for colleges, departments and classrooms.
            </p>
          </div>

          <div className="relative z-10 flex items-center gap-2 text-xs text-white/70">
            <ShieldCheck className="size-4" />
            Secured with encrypted, role-based access
          </div>
        </motion.div>

        {/* Right / form panel */}
        <motion.div
          initial={{ opacity: 0, x: 24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
          className="flex flex-col justify-center p-8 sm:p-12"
        >
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500">
              <GraduationCap className="size-5 text-white" />
            </div>
            <span className="font-display text-lg font-bold text-white">ExamPortal</span>
          </div>

          <h2 className="font-display text-2xl font-bold text-white">Welcome back</h2>
          <p className="mt-1.5 text-sm text-slate-400">
            Sign in with the credentials issued by your institution.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <Input
              label="Username"
              placeholder="jane.doe"
              icon={<User className="size-4" />}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              error={fieldErrors.username}
              autoComplete="username"
              autoFocus
            />
            <Input
              label="Password"
              type="password"
              placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"
              icon={<Lock className="size-4" />}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={fieldErrors.password}
              autoComplete="current-password"
            />

            <Button type="submit" size="lg" loading={loading} className="w-full group">
              Sign in
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
            </Button>
          </form>

          <p className="mt-8 text-center text-xs text-slate-600">
            Trouble signing in? Contact your college administrator.
          </p>
          <p className="mt-3 text-center text-xs text-slate-500">
            Applying to a college for the first time?{" "}
            <Link to="/signup" className="font-medium text-brand-300 hover:text-brand-200">
              Create an applicant account
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
