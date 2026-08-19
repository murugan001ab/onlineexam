import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import { GraduationCap, X } from "lucide-react";
import { NAV_BY_ROLE } from "./navConfig";
import type { RoleName } from "@/types/auth";
import { cn, humanizeRole } from "@/lib/utils";

interface SidebarProps {
  role: RoleName;
  studentStage?: "applicant" | "enrolled" | null;
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ role, studentStage, open, onClose }: SidebarProps) {
  const items = role === "student" && studentStage === "applicant"
    ? NAV_BY_ROLE[role].filter((item) => item.to === "/dashboard" || item.to === "/entrance")
    : NAV_BY_ROLE[role];

  return (
    <>
      {/* mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-white/10 bg-surface-900/80 backdrop-blur-2xl",
          "transition-transform duration-300 ease-out lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between gap-3 px-6 py-6">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-linear-to-br from-brand-500 to-accent-500 shadow-lg shadow-brand-500/30">
              <GraduationCap className="size-5 text-white" />
            </div>
            <div>
              <p className="font-display text-base font-bold text-white">ExamPortal</p>
              <p className="text-[11px] uppercase tracking-wider text-slate-500">
                {humanizeRole(role)}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white lg:hidden"
          >
            <X className="size-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-4 py-2">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  "group relative flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-colors duration-200",
                  isActive
                    ? "text-white"
                    : "text-slate-400 hover:bg-white/4 hover:text-slate-100",
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="active-nav-pill"
                      className="absolute inset-0 rounded-xl bg-linear-to-r from-brand-600/80 to-brand-500/60 shadow-lg shadow-brand-600/20"
                      transition={{ type: "spring", stiffness: 400, damping: 32 }}
                    />
                  )}
                  <item.icon className="relative z-10 size-4.5 shrink-0" />
                  <span className="relative z-10">{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-white/10 px-6 py-4">
          <p className="text-[11px] text-slate-600">v1.0.0 &middot; Online Exam Platform</p>
        </div>
      </aside>
    </>
  );
}
