import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { GraduationCap, Lock, User, Mail, Phone, ArrowRight, CheckCircle2, ShieldCheck } from "lucide-react";
import toast from "react-hot-toast";
import { publicSignupApi } from "@/api/publicSignup";
import { apiErrorMessage, tokenStorage } from "@/api/client";
import { useAuthStore } from "@/store/authStore";
import { AuroraBackground } from "@/components/ui/AuroraBackground";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";

interface FormState {
  collegeId: string;
  name: string;
  email: string;
  phone: string;
  password: string;
  confirmPassword: string;
  tenthMark: string;
  twelfthMark: string;
}

const emptyForm: FormState = {
  collegeId: "",
  name: "",
  email: "",
  phone: "",
  password: "",
  confirmPassword: "",
  tenthMark: "",
  twelfthMark: "",
};

export function SignupPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>(emptyForm);
  const [emailCode, setEmailCode] = useState("");
  const [phoneCode, setPhoneCode] = useState("");
  const [emailVerified, setEmailVerified] = useState(false);
  const [phoneVerified, setPhoneVerified] = useState(false);
  const [emailCodeSent, setEmailCodeSent] = useState(false);
  const [phoneCodeSent, setPhoneCodeSent] = useState(false);

  const { data: colleges = [], isLoading: loadingColleges } = useQuery({
    queryKey: ["public-colleges"],
    queryFn: publicSignupApi.listColleges,
  });

  function markEmailDirty(next: string) {
    setForm((f) => ({ ...f, email: next }));
    setEmailVerified(false);
    setEmailCodeSent(false);
    setEmailCode("");
  }
  function markPhoneDirty(next: string) {
    setForm((f) => ({ ...f, phone: next }));
    setPhoneVerified(false);
    setPhoneCodeSent(false);
    setPhoneCode("");
  }

  const sendEmailOtp = useMutation({
    mutationFn: () => publicSignupApi.sendOtp({ contact_type: "email", contact: form.email }),
    onSuccess: (res) => {
      setEmailCodeSent(true);
      if (res.debug_code) {
        setEmailCode(res.debug_code);
        toast.success(`Dev mode — no email server configured. Code: ${res.debug_code}`, { duration: 10000 });
      } else {
        toast.success("Verification code sent to your email");
      }
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not send the code")),
  });

  const sendPhoneOtp = useMutation({
    mutationFn: () => publicSignupApi.sendOtp({ contact_type: "phone", contact: form.phone }),
    onSuccess: (res) => {
      setPhoneCodeSent(true);
      if (res.debug_code) {
        setPhoneCode(res.debug_code);
        toast.success(`Dev mode — no SMS gateway configured. Code: ${res.debug_code}`, { duration: 10000 });
      } else {
        toast.success("Verification code sent to your phone");
      }
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not send the code")),
  });

  const verifyEmailOtp = useMutation({
    mutationFn: () => publicSignupApi.verifyOtp({ contact_type: "email", contact: form.email, code: emailCode }),
    onSuccess: () => {
      setEmailVerified(true);
      toast.success("Email verified");
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Incorrect or expired code")),
  });

  const verifyPhoneOtp = useMutation({
    mutationFn: () => publicSignupApi.verifyOtp({ contact_type: "phone", contact: form.phone, code: phoneCode }),
    onSuccess: () => {
      setPhoneVerified(true);
      toast.success("Phone verified");
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Incorrect or expired code")),
  });

  const submitMutation = useMutation({
    mutationFn: () =>
      publicSignupApi.register({
        college_id: Number(form.collegeId),
        name: form.name,
        email: form.email,
        phone: form.phone,
        password: form.password,
        tenth_mark: form.tenthMark ? Number(form.tenthMark) : undefined,
        twelfth_mark: form.twelfthMark ? Number(form.twelfthMark) : undefined,
      }),
    onSuccess: async (res) => {
      tokenStorage.setTokens(res.access_token, res.refresh_token);
      toast.success("Application account created — welcome!");
      await useAuthStore.getState().hydrate();
      navigate("/entrance", { replace: true });
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not create your account")),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.collegeId) return toast.error("Select your college");
    if (!emailVerified) return toast.error("Please verify your email first");
    if (!phoneVerified) return toast.error("Please verify your phone number first");
    if (form.password.length < 8) return toast.error("Password must be at least 8 characters");
    if (form.password !== form.confirmPassword) return toast.error("Passwords do not match");
    submitMutation.mutate();
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12">
      <AuroraBackground />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="glass-panel relative w-full max-w-xl p-8 sm:p-10"
      >
        <div className="mb-6 flex items-center gap-3">
          <div className="flex size-11 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500">
            <GraduationCap className="size-6 text-white" />
          </div>
          <div>
            <h1 className="font-display text-xl font-bold text-white">Create your applicant account</h1>
            <p className="text-sm text-slate-400">Verify your email and phone, then apply for an entrance exam.</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <Select
            label="College"
            required
            placeholder={loadingColleges ? "Loading colleges..." : "Select your college"}
            value={form.collegeId}
            onChange={(e) => setForm({ ...form, collegeId: e.target.value })}
            options={colleges.map((c) => ({ value: String(c.id), label: c.city ? `${c.name} — ${c.city}` : c.name }))}
          />

          <Input
            label="Full name"
            required
            icon={<User className="size-4" />}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />

          {/* Email + verification */}
          <div>
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <Input
                  label="Email"
                  type="email"
                  required
                  disabled={emailVerified}
                  icon={<Mail className="size-4" />}
                  value={form.email}
                  onChange={(e) => markEmailDirty(e.target.value)}
                />
              </div>
              {emailVerified ? (
                <span className="mb-0.5 flex h-11 items-center gap-1.5 rounded-xl border border-success-500/30 bg-success-500/10 px-3 text-xs font-medium text-success-400">
                  <CheckCircle2 className="size-4" /> Verified
                </span>
              ) : (
                <Button
                  type="button"
                  variant="glass"
                  className="mb-0.5 shrink-0"
                  disabled={!form.email || sendEmailOtp.isPending}
                  loading={sendEmailOtp.isPending}
                  onClick={() => sendEmailOtp.mutate()}
                >
                  {emailCodeSent ? "Resend" : "Send code"}
                </Button>
              )}
            </div>
            {emailCodeSent && !emailVerified && (
              <div className="mt-2 flex items-end gap-2">
                <Input
                  label="Email verification code"
                  value={emailCode}
                  onChange={(e) => setEmailCode(e.target.value)}
                  maxLength={8}
                />
                <Button
                  type="button"
                  className="mb-0.5 shrink-0"
                  disabled={!emailCode || verifyEmailOtp.isPending}
                  loading={verifyEmailOtp.isPending}
                  onClick={() => verifyEmailOtp.mutate()}
                >
                  Verify
                </Button>
              </div>
            )}
          </div>

          {/* Phone + verification */}
          <div>
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <Input
                  label="Mobile number"
                  required
                  disabled={phoneVerified}
                  icon={<Phone className="size-4" />}
                  value={form.phone}
                  onChange={(e) => markPhoneDirty(e.target.value)}
                />
              </div>
              {phoneVerified ? (
                <span className="mb-0.5 flex h-11 items-center gap-1.5 rounded-xl border border-success-500/30 bg-success-500/10 px-3 text-xs font-medium text-success-400">
                  <CheckCircle2 className="size-4" /> Verified
                </span>
              ) : (
                <Button
                  type="button"
                  variant="glass"
                  className="mb-0.5 shrink-0"
                  disabled={!form.phone || sendPhoneOtp.isPending}
                  loading={sendPhoneOtp.isPending}
                  onClick={() => sendPhoneOtp.mutate()}
                >
                  {phoneCodeSent ? "Resend" : "Send code"}
                </Button>
              )}
            </div>
            {phoneCodeSent && !phoneVerified && (
              <div className="mt-2 flex items-end gap-2">
                <Input
                  label="Mobile verification code"
                  value={phoneCode}
                  onChange={(e) => setPhoneCode(e.target.value)}
                  maxLength={8}
                />
                <Button
                  type="button"
                  className="mb-0.5 shrink-0"
                  disabled={!phoneCode || verifyPhoneOtp.isPending}
                  loading={verifyPhoneOtp.isPending}
                  onClick={() => verifyPhoneOtp.mutate()}
                >
                  Verify
                </Button>
              </div>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="10th mark (%)"
              type="number"
              min={0}
              max={100}
              value={form.tenthMark}
              onChange={(e) => setForm({ ...form, tenthMark: e.target.value })}
            />
            <Input
              label="12th mark (%)"
              type="number"
              min={0}
              max={100}
              value={form.twelfthMark}
              onChange={(e) => setForm({ ...form, twelfthMark: e.target.value })}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Password"
              type="password"
              required
              minLength={8}
              icon={<Lock className="size-4" />}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
            <Input
              label="Confirm password"
              type="password"
              required
              minLength={8}
              icon={<Lock className="size-4" />}
              value={form.confirmPassword}
              onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
            />
          </div>

          <div className="flex items-center gap-2 rounded-xl border border-brand-500/20 bg-brand-500/5 px-3.5 py-2.5 text-xs text-brand-300">
            <ShieldCheck className="size-4 shrink-0" />
            You'll be able to apply for an entrance exam right after this — as soon as your college opens one.
          </div>

          <Button type="submit" size="lg" className="w-full group" loading={submitMutation.isPending}>
            Create account
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-slate-500">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-brand-300 hover:text-brand-200">
            Sign in
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
