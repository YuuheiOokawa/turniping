import Link from "next/link";

const NAV = [
  { href: "/dashboard", label: "ダッシュボード" },
  { href: "/news", label: "ニュース" },
  { href: "/accuracy", label: "的中率" },
  { href: "/paper", label: "ペーパートレード" },
  { href: "/ai-trading", label: "AI自動売買" },
  { href: "/guide", label: "用語ガイド" },
  { href: "/system", label: "システム" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-neutral-200 dark:border-neutral-800">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
          <span className="text-lg font-bold">turniping</span>
          <nav className="flex gap-4 text-sm text-neutral-600 dark:text-neutral-300">
            {NAV.map((item) => (
              <Link key={item.href} href={item.href} className="hover:text-neutral-900 dark:hover:text-white">
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-6">{children}</main>
    </div>
  );
}
