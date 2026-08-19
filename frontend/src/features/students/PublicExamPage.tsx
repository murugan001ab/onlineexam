import { Link, useParams } from "react-router-dom";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Building2,
  Calendar,
  Clock,
  FileSpreadsheet,
  ShieldCheck,
  Users2,
  Wallet,
} from "lucide-react";
import { publicSignupApi } from "@/api/publicSignup";
import { apiErrorMessage } from "@/api/client";
import { AuroraBackground } from "@/components/ui/AuroraBackground";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { formatCurrency, formatDateTime } from "@/lib/utils";

/**
 * Unauthenticated landing page for an exam's shareable link
 * (FRONTEND_URL/e/{slug}) — the page a WhatsApp message, poster QR code, or
 * college-portal link points at. Shows the exam summary from
 * GET /public/exams/{slug} and hands the visitor off to signup/login so
 * they land back ready to register once they have an account.
 */
export function PublicExamPage() {
  const { slug = "" } = useParams<{ slug: string }>();

  const {
    data: exam,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["public-exam", slug],
    queryFn: () => publicSignupApi.getExamBySlug(slug),
    enabled: !!slug,
    retry: false,
  });

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12">
      <AuroraBackground />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="glass-panel relative w-full max-w-xl p-8 sm:p-10"
      >
        {isLoading && (
          <div className="flex flex-col items-center gap-3 py-10">
            <Spinner size={28} />
            <p className="text-sm text-slate-500">Loading exam details&hellip;</p>
          </div>
        )}

        {isError && (
          <div className="py-10 text-center">
            <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-2xl bg-danger-500/10 text-danger-400 ring-1 ring-inset ring-danger-500/20">
              <FileSpreadsheet className="size-6" />
            </div>
            <h1 className="font-display text-lg font-bold text-white">This link isn&apos;t available</h1>
            <p className="mt-2 text-sm text-slate-400">
              {apiErrorMessage(error, "This exam link is invalid, expired, or no longer active.")}
            </p>
            <Link to="/login" className="mt-6 inline-block text-sm font-medium text-brand-300 hover:text-brand-200">
              Go to sign in
            </Link>
          </div>
        )}

        {exam && (
          <>
            <div className="mb-6 flex items-center gap-3">
              <div className="flex size-11 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500">
                <FileSpreadsheet className="size-6 text-white" />
              </div>
              <div>
                <h1 className="font-display text-xl font-bold text-white">{exam.name}</h1>
                <p className="flex items-center gap-1.5 text-sm text-slate-400">
                  <Building2 className="size-3.5" /> {exam.college_name}
                  {exam.exam_type_name && <span className="text-slate-600">&middot; {exam.exam_type_name}</span>}
                </p>
              </div>
            </div>

            {exam.description && <p className="mb-6 text-sm leading-relaxed text-slate-300">{exam.description}</p>}

            <div className="mb-6 grid gap-3 sm:grid-cols-2">
              <InfoRow icon={<Calendar className="size-4" />} label="Starts" value={formatDateTime(exam.starts_at)} />
              <InfoRow
                icon={<Clock className="size-4" />}
                label="Duration"
                value={exam.duration_minutes ? `${exam.duration_minutes} min` : "—"}
              />
              <InfoRow
                icon={<Wallet className="size-4" />}
                label="Registration fee"
                value={formatCurrency(exam.fee, exam.fee_currency)}
              />
              <InfoRow
                icon={<Users2 className="size-4" />}
                label="Open slots"
                value={exam.open_slot_count > 0 ? `${exam.open_slot_count} available` : "None open yet"}
              />
            </div>

            <div className="mb-6 flex items-center gap-2 rounded-xl border border-brand-500/20 bg-brand-500/5 px-3.5 py-2.5 text-xs text-brand-300">
              <ShieldCheck className="size-4 shrink-0" />
              This is a proctored online exam — tab switches, fullscreen exits, and (if enabled) camera checks
              are monitored during your attempt.
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <Link to="/signup" state={{ from: "/entrance/apply" }} className="flex-1">
                <Button size="lg" className="w-full group">
                  Register for this exam
                  <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
                </Button>
              </Link>
              <Link to="/login" state={{ from: "/entrance/apply" }} className="flex-1">
                <Button size="lg" variant="glass" className="w-full">
                  I already have an account
                </Button>
              </Link>
            </div>
          </>
        )}
      </motion.div>
    </div>
  );
}

function InfoRow({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2.5">
      <span className="text-slate-500">{icon}</span>
      <div>
        <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
        <p className="text-sm font-medium text-slate-200">{value}</p>
      </div>
    </div>
  );
}
