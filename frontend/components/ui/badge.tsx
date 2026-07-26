import { cn } from "@/lib/utils";

export function Badge({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-white/10 bg-white/8 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-slate-300",
        className
      )}
    >
      {children}
    </span>
  );
}
