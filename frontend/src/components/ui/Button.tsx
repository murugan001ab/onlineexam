import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "relative inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl font-medium " +
    "transition-all duration-200 ease-out select-none " +
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-950 " +
    "disabled:pointer-events-none disabled:opacity-50 active:scale-[0.97]",
  {
    variants: {
      variant: {
        primary:
          "bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-lg shadow-brand-600/25 " +
          "hover:shadow-xl hover:shadow-brand-500/40 hover:brightness-110",
        accent:
          "bg-gradient-to-r from-accent-500 to-brand-500 text-white shadow-lg shadow-accent-500/25 " +
          "hover:shadow-xl hover:shadow-accent-500/40 hover:brightness-110",
        glass:
          "border border-white/15 bg-white/[0.06] text-slate-100 backdrop-blur-xl hover:bg-white/[0.12] hover:border-white/25",
        ghost: "text-slate-300 hover:bg-white/[0.06] hover:text-white",
        danger:
          "bg-gradient-to-r from-danger-500 to-rose-600 text-white shadow-lg shadow-danger-500/25 hover:shadow-xl hover:brightness-110",
        outline:
          "border border-brand-500/40 text-brand-300 hover:bg-brand-500/10 hover:border-brand-400",
      },
      size: {
        sm: "h-9 px-3.5 text-sm",
        md: "h-11 px-5 text-sm",
        lg: "h-12 px-7 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="size-4 animate-spin" />}
      {children}
    </button>
  ),
);
Button.displayName = "Button";
