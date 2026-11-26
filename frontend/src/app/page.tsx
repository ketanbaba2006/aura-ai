"use client";

import { AppShell } from "@/components/layout/AppShell";
import { NotificationProvider } from "@/context/NotificationContext";
import { AuthProvider } from "@/context/AuthContext";

export default function Home() {
  return (
    <AuthProvider>
      <NotificationProvider>
        <AppShell />
      </NotificationProvider>
    </AuthProvider>
  );
}

