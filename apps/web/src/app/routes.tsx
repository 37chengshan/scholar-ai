import { createBrowserRouter, Navigate } from "react-router";
import { lazy, Suspense } from "react";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { ForgotPassword } from "./pages/ForgotPassword";
import { ResetPassword } from "./pages/ResetPassword";
import { Layout } from "./components/Layout";
import { LoadingFallback } from "./components/LoadingFallback";
import { hasWarmAuthHint, useAuth } from "@/contexts/AuthContext";
import { Dashboard } from "./pages/Dashboard";
import { Chat } from "./pages/Chat";

// Lazy load pages (Landing and Login/Register are critical, keep as regular imports)
const KnowledgeBaseList = lazy(() => import("./pages/KnowledgeBaseList").then(m => ({ default: m.KnowledgeBaseList })));
const KnowledgeBaseDetail = lazy(() => import("./pages/KnowledgeBaseDetail").then(m => ({ default: m.KnowledgeBaseDetail })));
const Search = lazy(() => import("./pages/Search").then(m => ({ default: m.Search })));
const Read = lazy(() => import("./pages/Read").then(m => ({ default: m.Read })));
const Settings = lazy(() => import("./pages/Settings").then(m => ({ default: m.Settings })));
const Notes = lazy(() => import("./pages/Notes").then(m => ({ default: m.Notes })));
const Analytics = lazy(() => import("./pages/Analytics").then(m => ({ default: m.Analytics })));
const Compare = lazy(() => import("./pages/Compare").then(m => ({ default: m.Compare })));

// Auth guard component for protected routes
// Uses AuthContext (Cookie-based auth) instead of localStorage
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const warmAuthHint = hasWarmAuthHint();

  // Show loading state while checking auth
  if (loading && !isAuthenticated && !warmAuthHint) {
    return <LoadingFallback />;
  }

  // Redirect to login if not authenticated
  if (!loading && !isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

// Suspense wrapper for lazy-loaded components
function LazyRoute({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<LoadingFallback />}>
      {children}
    </Suspense>
  );
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: "/home",
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: "/login",
    Component: Login,
  },
  {
    path: "/register",
    Component: Register,
  },
  {
    path: "/forgot-password",
    Component: ForgotPassword,
  },
  {
    path: "/reset-password",
    Component: ResetPassword,
  },
  {
    // Layout is a wrapper for all app pages, no path needed
    element: <Layout />,
    children: [
      {
        path: "workspace",
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: "knowledge-bases",
        element: <LazyRoute><ProtectedRoute><KnowledgeBaseList /></ProtectedRoute></LazyRoute>,
      },
      {
        path: "knowledge-bases/:id",
        element: <LazyRoute><ProtectedRoute><KnowledgeBaseDetail /></ProtectedRoute></LazyRoute>,
      },
      {
        path: "search",
        element: <LazyRoute><ProtectedRoute><Search /></ProtectedRoute></LazyRoute>,
      },
      {
        path: "read/:id",
        element: <LazyRoute><ProtectedRoute><Read /></ProtectedRoute></LazyRoute>,
      },
      {
        path: "read",
        element: <LazyRoute><ProtectedRoute><Read /></ProtectedRoute></LazyRoute>,
      },
      {
        path: "chat",
        element: <LazyRoute><ProtectedRoute><Chat /></ProtectedRoute></LazyRoute>,
      },
      {
        path: "settings",
        element: <LazyRoute><ProtectedRoute><Settings /></ProtectedRoute></LazyRoute>,
      },
      {
        path: "notes",
        element: <LazyRoute><ProtectedRoute><Notes /></ProtectedRoute></LazyRoute>,
      },
      {
        path: "dashboard",
        element: <LazyRoute><ProtectedRoute><Dashboard /></ProtectedRoute></LazyRoute>,
      },
      {
        path: "analytics",
        element: <LazyRoute><ProtectedRoute><Analytics /></ProtectedRoute></LazyRoute>,
      },
      {
        path: "compare",
        element: <LazyRoute><ProtectedRoute><Compare /></ProtectedRoute></LazyRoute>,
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
]);
