import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { Inbox } from "lucide-react";
import { Spinner } from "./Spinner";
import { cn } from "@/lib/utils";

export interface Column<T> {
  header: string;
  accessor: (row: T) => ReactNode;
  className?: string;
  headerClassName?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (row: T) => string | number;
  loading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  rowActions?: (row: T) => ReactNode;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  loading,
  emptyTitle = "No records yet",
  emptyDescription = "Once you create some, they'll show up here.",
  rowActions,
}: DataTableProps<T>) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-20">
        <Spinner size={28} />
        <p className="text-sm text-slate-500">Loading&hellip;</p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-20 text-center">
        <div className="flex size-14 items-center justify-center rounded-2xl bg-white/[0.04] text-slate-600 ring-1 ring-inset ring-white/10">
          <Inbox className="size-6" />
        </div>
        <div>
          <p className="font-medium text-slate-300">{emptyTitle}</p>
          <p className="mt-1 text-sm text-slate-500">{emptyDescription}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-white/10">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-white/10 bg-white/[0.03]">
            {columns.map((col) => (
              <th
                key={col.header}
                className={cn(
                  "px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500",
                  col.headerClassName,
                )}
              >
                {col.header}
              </th>
            ))}
            {rowActions && <th className="px-4 py-3" />}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <motion.tr
              key={keyExtractor(row)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.25, delay: Math.min(i * 0.03, 0.3) }}
              className="border-b border-white/5 transition-colors last:border-0 hover:bg-white/[0.03]"
            >
              {columns.map((col) => (
                <td key={col.header} className={cn("px-4 py-3.5 text-slate-300", col.className)}>
                  {col.accessor(row)}
                </td>
              ))}
              {rowActions && (
                <td className="px-4 py-3.5 text-right">
                  <div className="flex justify-end gap-1">{rowActions(row)}</div>
                </td>
              )}
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
