import Link from "next/link";
import { MarketingNav } from "@/components/marketing-nav";
import { Wordmark } from "@/components/brand";

const LEGAL_LINKS = [
  { href: "/legal/terms", label: "Terms" },
  { href: "/legal/privacy", label: "Privacy" },
  { href: "/legal/dpa", label: "DPA" },
  { href: "/legal/subprocessors", label: "Subprocessors" },
];

/** Shared chrome + prose styling for the legal pages. */
export function LegalShell({
  title,
  updated,
  children,
}: {
  title: string;
  updated: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-dvh bg-background">
      <MarketingNav />
      <article className="container max-w-3xl py-14">
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">Last updated: {updated}</p>

        <div className="mt-8 space-y-6 text-sm leading-relaxed text-muted-foreground [&_h2]:mt-8 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:text-foreground [&_a]:text-accent [&_a]:underline-offset-2 hover:[&_a]:underline [&_strong]:text-foreground [&_ul]:list-disc [&_ul]:space-y-1.5 [&_ul]:pl-5 [&_table]:w-full [&_table]:text-xs [&_th]:py-2 [&_th]:text-left [&_th]:font-medium [&_th]:text-foreground [&_td]:border-t [&_td]:border-border [&_td]:py-2">
          {children}
        </div>

        <p className="mt-10 rounded-lg border border-border bg-muted/40 p-4 text-xs text-muted-foreground">
          This is a plain-language template provided for transparency, not legal advice. Before
          commercial launch, have it reviewed by qualified counsel and insert your legal entity and
          contact details.
        </p>
      </article>

      <footer className="border-t border-border/60">
        <div className="container flex flex-wrap items-center justify-between gap-4 py-8">
          <Wordmark />
          <nav className="flex flex-wrap gap-4">
            {LEGAL_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>
      </footer>
    </div>
  );
}
