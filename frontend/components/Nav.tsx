"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/", label: "首页", icon: "M3 12l9-9 9 9M5 10v10h5v-6h4v6h5V10" },
  { href: "/library", label: "学习资料", icon: "M4 6a2 2 0 012-2h4l2 2h6a2 2 0 012 2v10a2 2 0 01-2 2H6a2 2 0 01-2-2V6z" },
  { href: "/chat", label: "AI 对话", icon: "M21 12a8 8 0 01-8 8H4l2.5-2.5A8 8 0 1121 12z" },
  { href: "/summary", label: "自动总结", icon: "M9 12h6M9 16h4M7 4h10a2 2 0 012 2v14l-3-2-3 2-3-2-3 2V6a2 2 0 012-2z" },
  { href: "/quiz", label: "练习", icon: "M12 20h9M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4L16.5 3.5z" },
  { href: "/wrong-questions", label: "错题本", icon: "M12 6.3c-1.6-2-4.4-2.6-6.5-1a6.6 6.6 0 00-1 9.6L12 21l7.5-6.1a6.6 6.6 0 00-1-9.6c-2.1-1.6-4.9-1-6.5 1z" },
  { href: "/settings", label: "设置", icon: "M10.3 4.3a1.5 1.5 0 013 0l.5 1.4a1.5 1.5 0 001.9.9l1.4-.4a1.5 1.5 0 012.1 2.1l-.4 1.4a1.5 1.5 0 00.9 1.9l1.4.5a1.5 1.5 0 010 3l-1.4.5a1.5 1.5 0 00-.9 1.9l.4 1.4a1.5 1.5 0 01-2.1 2.1l-1.4-.4a1.5 1.5 0 00-1.9.9l-.5 1.4a1.5 1.5 0 01-3 0l-.5-1.4a1.5 1.5 0 00-1.9-.9l-1.4.4a1.5 1.5 0 01-2.1-2.1l.4-1.4a1.5 1.5 0 00-.9-1.9l-1.4-.5a1.5 1.5 0 010-3l1.4-.5a1.5 1.5 0 00.9-1.9l-.4-1.4a1.5 1.5 0 012.1-2.1l1.4.4a1.5 1.5 0 001.9-.9l.5-1.4z" },
];

function Icon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5 shrink-0">
      <path d={d} />
    </svg>
  );
}

export default function Nav() {
  const pathname = usePathname();

  // 桌面左侧栏
  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-52 flex-col border-r border-zinc-200 bg-white lg:flex">
        <Link href="/" className="flex items-center gap-2 px-5 py-5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
            学
          </span>
          <span className="text-sm font-semibold text-zinc-900">AI 学习助手</span>
        </Link>
        <nav className="flex-1 space-y-0.5 px-2.5">
          {ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                  active ? "bg-indigo-50 font-medium text-indigo-700" : "text-zinc-600 hover:bg-zinc-100"
                }`}
              >
                <Icon d={item.icon} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="px-5 py-4 text-xs text-zinc-400">本地优先 · 资料只属于你</div>
      </aside>

      {/* 移动端：顶部栏 + 底部导航 */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-zinc-200 bg-white/95 px-4 py-3 backdrop-blur lg:hidden">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-xs font-bold text-white">学</span>
          <span className="text-sm font-semibold text-zinc-900">AI 学习助手</span>
        </Link>
        <div className="flex items-center gap-1">
          <Link href="/wrong-questions" className={`rounded-lg p-2 ${pathname === "/wrong-questions" ? "bg-indigo-50 text-indigo-700" : "text-zinc-500"}`}>
            <Icon d={ITEMS[5].icon} />
          </Link>
          <Link href="/settings" className={`rounded-lg p-2 ${pathname === "/settings" ? "bg-indigo-50 text-indigo-700" : "text-zinc-500"}`}>
            <Icon d={ITEMS[6].icon} />
          </Link>
        </div>
      </header>
      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-zinc-200 bg-white pb-[env(safe-area-inset-bottom)] lg:hidden">
        {ITEMS.slice(0, 5).map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center gap-0.5 py-2 text-[11px] ${
                active ? "text-indigo-600" : "text-zinc-500"
              }`}
            >
              <Icon d={item.icon} />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
