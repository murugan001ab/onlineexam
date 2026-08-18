import type { ReactNode } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
  {
    variants: {
      variant: {
        brand: "bg-brand-500/15 text-brand-300 ring-1 ring-inset ring-brand-500/30",
        accent: "bg-accent-500/15 text-accent-300 ring-1 ring-inset ring-accent-500/30",
        success: "bg-success-500/15 text-emerald-300 ring-1 ring-inset ring-success-500/30",
        warning: "bg-warning-500/15 text-amber-300 ring-1 ring-inset ring-warning-500/30",
        danger: "bg-danger-500/15 text-rose-300 ring-1 ring-inset ring-danger-500/30",
        neutral: "bg-white/[0.06] text-slate-300 ring-1 ring-inset ring-white/10",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

export interface BadgeProps extends VariantProps<typeof badgeVariants> {
  children: ReactNode;
  className?: string;
  dot?: boolean;
}

export function Badge({ variant, children, className, dot }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)}>
      {dot && <span className="size-1.5 animate-pulse rounded-full bg-current" />}
      {children}
    </span>
  );
}
