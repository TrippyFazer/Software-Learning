import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router-dom";
import { api, ApiError } from "./api";
import Layout from "./components/Layout";
import AboutServer from "./pages/AboutServer";
import Challenge from "./pages/Challenge";
import Curriculum from "./pages/Curriculum";
import Dashboard from "./pages/Dashboard";
import LessonPage from "./pages/Lesson";
import Login from "./pages/Login";
import OfflinePage from "./pages/Offline";
import Practice from "./pages/Practice";
import ProgressPage from "./pages/Progress";
import Review from "./pages/Review";
import Vocabulary from "./pages/Vocabulary";
import type { Me } from "./types";

/**
 * The identity of the last person who successfully signed in.
 *
 * This is NOT a credential and grants nothing: the real session is an HttpOnly
 * cookie the browser holds and the server validates. This only answers "whose
 * name goes in the sidebar, and should I render the app or the login form?"
 *
 * It exists because without it the app is unusable offline. The boot sequence
 * calls /api/auth/me; with no network that request fails; the old code treated
 * every failure as "not logged in" and showed the login form — which then also
 * could not reach the server. Everything was cached and none of it reachable.
 *
 * Sessions last SESSION_TTL_HOURS (14 days), so a cookie taken on the ground
 * is still valid when you land.
 */
const ME_KEY = "ill.me";

function readCachedMe(): Me | null {
  try {
    const raw = localStorage.getItem(ME_KEY);
    return raw ? (JSON.parse(raw) as Me) : null;
  } catch {
    return null;
  }
}

export function cacheMe(me: Me | null): void {
  try {
    if (me) localStorage.setItem(ME_KEY, JSON.stringify(me));
    else localStorage.removeItem(ME_KEY);
  } catch {
    /* private browsing / storage disabled — degrade to online-only */
  }
}

export default function App() {
  const me = useQuery<Me>({
    queryKey: ["me"],
    queryFn: async () => {
      const data = await api.get<Me>("/api/auth/me");
      cacheMe(data);
      return data;
    },
    retry: (count, err) => !(err instanceof ApiError && err.status === 401) && count < 2,
  });

  if (me.isLoading) {
    return <div className="login-wrap muted mono">loading…</div>;
  }

  if (me.isError) {
    // A 401 is the server actively saying "you are not signed in" — the cached
    // identity is stale and must be discarded, or you would be stuck looking
    // at a shell you have no session for.
    const rejected = me.error instanceof ApiError && me.error.status === 401;
    if (rejected) {
      cacheMe(null);
      return <Login />;
    }
    // Anything else is a transport failure. If we know who was last signed in,
    // carry on offline; the cookie is still in the browser and will be sent
    // the moment there is a network again.
    const cached = readCachedMe();
    if (cached) return <Shell me={cached} />;
    return <Login />;
  }

  return <Shell me={me.data!} />;
}

function Shell({ me }: { me: Me }) {
  return (
    <Layout me={me}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/curriculum" element={<Curriculum />} />
        <Route path="/lessons/:module/:lesson" element={<LessonPage />} />
        <Route path="/practice" element={<Practice />} />
        <Route path="/practice/:module/:name" element={<Practice />} />
        <Route path="/challenges/:name" element={<Challenge />} />
        <Route path="/vocabulary" element={<Vocabulary />} />
        <Route path="/review" element={<Review />} />
        <Route path="/progress" element={<ProgressPage />} />
        <Route path="/offline" element={<OfflinePage />} />
        <Route path="/about-server" element={<AboutServer />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
