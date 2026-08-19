import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { NAV_BY_ROLE } from "@/components/layout/navConfig";
import { humanizeRole } from "@/lib/utils";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};
const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0 },
};

export function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  if (!user) return null;

  const modules = NAV_BY_ROLE[user.role].filter((n) => n.to !== "/dashboard").filter((n) =>
    user.role !== "student" || user.student_stage !== "applicant" || n.to === "/entrance",
  );

  return (
    <div>
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-white sm:text-3xl">
            Welcome, <span className="text-gradient">{user.username}</span>
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Here&apos;s what&apos;s happening across your {humanizeRole(user.role).toLowerCase()} workspace.
          </p>
        </div>
        <Badge variant="brand" dot>
          <Sparkles className="size-3" /> Batch 1 &mdash; Auth &amp; Shell live
        </Badge>
      </div>

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3"
      >
        {modules.map((m) => (
          <motion.div key={m.to} variants={item}>
            <Card className="group cursor-pointer" onClick={() => navigate(m.to)}>
              <CardHeader>
                <div className="flex size-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500/20 to-accent-500/20 text-brand-300 ring-1 ring-inset ring-brand-500/20 transition-transform duration-300 group-hover:scale-110">
                  <m.icon className="size-5" />
                </div>
              </CardHeader>
              <CardTitle>{m.label}</CardTitle>
              <p className="mt-1.5 text-sm text-slate-500">
                Manage {m.label.toLowerCase()} for your organization.
              </p>
            </Card>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}
