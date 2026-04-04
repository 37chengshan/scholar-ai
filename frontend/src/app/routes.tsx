import { createBrowserRouter, Navigate } from "react-router";
import { lazy, Suspense } from "react";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/Login";
import { ForgotPassword } from "./pages/ForgotPassword";
import { ResetPassword } from "./pages/ResetPassword";
import { Layout } from "./components/Layout";
import { LoadingFallback } from "./components/LoadingFallback";
import { useAuth } from "@/contexts/AuthContext";

// Lazy load pages (Landing and Login are critical, keep as regular imports)
const Dashboard = lazy(() => import("./pages/Dashboard").then(m => ({ default: m.Dashboard })));
const Library = lazy(() => import("./pages/Library").then(m => ({ default: m.Library })));
const Search = lazy(() => import("./pages/Search").then(m => ({ default: m.Search })));
const Read = lazy(() => import("./pages/Read").then(m => ({ default: m.Read })));
const Chat = lazy(() => import("./pages/Chat").then(m => ({ default: m.Chat })));
const Upload = lazy(() => import("./pages/Upload").then(m => ({ default: m.Upload })));
const Settings = lazy(() => import("./pages/Settings").then(m => ({ default: m.Settings })));

// Auth guard component for protected routes
// Uses AuthContext (Cookie-based auth) instead of localStorage
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  // Show loading state while checking auth
  if (loading) {
    return <LoadingFallback />;
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
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
    Component: Landing,
  },
  {
    path: "/login",
    Component: Login,
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
        path: "dashboard",
        element: <LazyRoute><ProtectedRoute><Dashboard /></ProtectedRoute></LazyRoute>,
      },
      {
        path: "library",
        element: <LazyRoute><ProtectedRoute><Library /></ProtectedRoute></LazyRoute>,
      },
      {
        path: "search",
        element: <LazyRoute><ProtectedRoute><Search /></ProtectedRoute></LazyRoute>,
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
        path: "upload",
        element: <LazyRoute><ProtectedRoute><Upload /></ProtectedRoute></LazyRoute>,
      },
      {
        path: "settings",
        element: <LazyRoute><ProtectedRoute><Settings /></ProtectedRoute></LazyRoute>,
      },
    ],
  },
]);