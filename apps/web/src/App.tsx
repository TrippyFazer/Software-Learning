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
import Practice from "./pages/Practice";
import ProgressPage from "./pages/Progress";
import Review from "./pages/Review";
import Vocabulary from "./pages/Vocabulary";
import type { Me } from "./types";

export default function App() {
  const me = useQuery<Me>({
    queryKey: ["me"],
    queryFn: () => api.get<Me>("/api/auth/me"),
    retry: (count, err) => !(err instanceof ApiError && err.status === 401) && count < 2,
  });

  if (me.isLoading) {
    return <div className="login-wrap muted mono">loading…</div>;
  }

  if (me.isError) {
    return <Login />;
  }

  return (
    <Layout me={me.data!}>
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
        <Route path="/about-server" element={<AboutServer />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
