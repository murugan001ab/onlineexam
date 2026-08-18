import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { MeResponse } from "@/types/auth";
import { tokenStorage } from "@/api/client";
import * as authApi from "@/api/auth";

interface AuthState {
  user: MeResponse | null;
  status: "idle" | "authenticating" | "authenticated" | "unauthenticated";
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hydrate: () => Promise<void>;
  setError: (message: string | null) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      status: "idle",
      error: null,

      login: async (username, password) => {
        set({ status: "authenticating", error: null });
        try {
          const user = await authApi.login({ username, password });
          set({ user, status: "authenticated", error: null });
        } catch (err) {
          set({ status: "unauthenticated" });
          throw err;
        }
      },

      logout: () => {
        authApi.logout();
        set({ user: null, status: "unauthenticated", error: null });
      },

      hydrate: async () => {
        if (!tokenStorage.getAccess()) {
          set({ status: "unauthenticated" });
          return;
        }
        try {
          const user = await authApi.fetchMe();
          set({ user, status: "authenticated" });
        } catch {
          tokenStorage.clear();
          set({ user: null, status: "unauthenticated" });
        }
      },

      setError: (message) => set({ error: message }),
    }),
    {
      name: "oe-auth",
      partialize: (state) => ({ user: state.user }),
    },
  ),
);

// Cross-tab / interceptor-triggered logout
window.addEventListener("auth:logout", () => {
  useAuthStore.setState({ user: null, status: "unauthenticated" });
});
