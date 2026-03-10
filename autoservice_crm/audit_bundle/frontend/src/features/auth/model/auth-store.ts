"use client";

import { create } from "zustand";

import type { AuthSession } from "@/features/auth/types/auth-types";

export type SessionStatus = "loading" | "authenticated" | "unauthenticated";

type AuthState = {
  session: AuthSession | null;
  status: SessionStatus;
  setLoading: () => void;
  setSession: (session: AuthSession) => void;
  setUnauthenticated: () => void;
  clearSession: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  session: null,
  status: "loading",
  setLoading: () => set({ status: "loading" }),
  setSession: (session) => set({ session, status: "authenticated" }),
  setUnauthenticated: () => set({ session: null, status: "unauthenticated" }),
  clearSession: () => set({ session: null, status: "unauthenticated" })
}));
