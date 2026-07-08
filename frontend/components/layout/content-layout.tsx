import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import type { ReactNode } from "react";

type ContentLayoutProps = {
  title: string;
  description?: string;
  children: ReactNode;
};

export function ContentLayout({ title, description, children }: ContentLayoutProps) {
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header title={title} description={description} />
        <main className="flex-1 px-8 py-6">{children}</main>
      </div>
    </div>
  );
}
