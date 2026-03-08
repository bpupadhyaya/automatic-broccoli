import type { PropsWithChildren } from "react";

interface PageCardProps extends PropsWithChildren {
  title?: string;
  subtitle?: string;
}

export default function PageCard({ title, subtitle, children }: PageCardProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      {(title || subtitle) && (
        <header className="mb-4 border-b border-slate-100 pb-3">
          {title && <h2 className="text-lg font-semibold text-slate-900">{title}</h2>}
          {subtitle && <p className="mt-1 text-sm text-slate-600">{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  );
}
