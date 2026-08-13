"use client";

/**
 * Session context — nguồn sự thật về "đang đăng nhập hay chưa" cho toàn app.
 *
 * Bootstrap từ localStorage nên có một nhịp `status === "loading"` ở lần render
 * đầu: token nằm trong localStorage, mà localStorage không tồn tại lúc SSR. Nếu
 * render thẳng theo `readTokens()` thì server render "chưa đăng nhập" còn client
 * render "đã đăng nhập" → hydration mismatch. Route guard phải chờ hết nhịp này
 * rồi mới đá user đi, không thì user đang đăng nhập vẫn bị bắn về /dang-nhap.
 */

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import {
  clearTokens,
  readTokens,
  subscribeTokens,
  writeTokens,
  type StoredTokens,
} from "./token-store";

export type SessionStatus = "loading" | "authenticated" | "guest";

export type Session = {
  status: SessionStatus;
  activeWorkspaceId: string | null;
  needsOnboarding: boolean;
  signIn: (tokens: StoredTokens) => void;
  signOut: () => Promise<void>;
};

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const router = useRouter();

  // `getServerSnapshot` trả undefined để lần render đầu (SSR và hydrate) luôn là
  // "loading" — localStorage chưa tồn tại lúc đó, đoán bừa sẽ lệch với client.
  const tokens = useSyncExternalStore(
    subscribeTokens,
    readTokens,
    () => undefined,
  );

  const status: SessionStatus =
    tokens === undefined ? "loading" : tokens ? "authenticated" : "guest";

  const signIn = useCallback((next: StoredTokens) => {
    writeTokens(next);
  }, []);

  const signOut = useCallback(async () => {
    const currentTokens = readTokens();
    try {
      if (currentTokens?.refreshToken) {
        const baseUrl =
          process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
        await fetch(`${baseUrl}/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: currentTokens.refreshToken }),
        });
      }
    } catch {
      // Đăng xuất phía client vẫn phải hoàn tất nếu API/network đang lỗi.
    } finally {
      clearTokens();
      router.replace("/login");
    }
  }, [router]);

  const value = useMemo<Session>(
    () => ({
      status,
      activeWorkspaceId: tokens?.activeWorkspaceId ?? null,
      needsOnboarding: tokens?.needsOnboarding ?? false,
      signIn,
      signOut,
    }),
    [status, tokens, signIn, signOut],
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) {
    throw new Error("useSession phải nằm trong <SessionProvider>");
  }
  return session;
}
