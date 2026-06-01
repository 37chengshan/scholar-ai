import { createBrowserRouter, Navigate, useLocation } from "react-router";
import { lazy, Suspense, Component, type ReactNode } from "react";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { ForgotPassword } from "./pages/ForgotPassword";
import { ResetPassword } from "./pages/ResetPassword";
import { Landing } from "./pages/Landing";
import { Layout } from "./components/Layout";
import { LoadingFallback } from "./components/LoadingFallback";
import { PageErrorFallback } from "./components/PageErrorFallback";
import {
  SearchResultsSkeleton,
  KnowledgeBaseSkeleton,
  AnalyticsSkeleton,
  NotesSkeleton,
} from "./components/PageSkeletons";
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
  const location = useLocation();

  // Show loading state while checking auth
  if (loading && !isAuthenticated && !warmAuthHint) {
    return <LoadingFallback />;
  }

  // Redirect to login if not authenticated
  if (!loading && !isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: `${location.pathname}${location.search}${location.hash}` }}
      />
    );
  }

  return <>{children}</>;
}

export function PublicAuthRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (!loading && isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

// Suspense wrapper for lazy-loaded components
function LazyRoute({ children, fallback }: { children: React.ReactNode; fallback?: ReactNode }) {
  return (
    <Suspense fallback={fallback ?? <LoadingFallback />}>
      {children}
    </Suspense>
  );
}

// Route-level error boundary using PageErrorFallback
interface RouteErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class RouteErrorBoundary extends Component<
  { children: ReactNode },
  RouteErrorBoundaryState
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): RouteErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("Route error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      return (
        <PageErrorFallback
          error={this.state.error}
          resetError={this.handleReset}
        />
      );
    }
    return this.props.children;
  }
}

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Landing,
  },
  {
    path: "/home",
    Component: Landing,
  },
  {
    path: "/login",
    Component: Login,
  },
  {
    path: "/register",
    element: <PublicAuthRoute><Register /></PublicAuthRoute>,
  },
  {
    path: "/forgot-password",
    element: <PublicAuthRoute><ForgotPassword /></PublicAuthRoute>,
  },
  {
    path: "/reset-password",
    element: <PublicAuthRoute><ResetPassword /></PublicAuthRoute>,
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
        element: <RouteErrorBoundary><LazyRoute fallback={<KnowledgeBaseSkeleton />}><ProtectedRoute><KnowledgeBaseList /></ProtectedRoute></LazyRoute></RouteErrorBoundary>,
      },
      {
        path: "knowledge-bases/:id",
        element: <RouteErrorBoundary><LazyRoute fallback={<KnowledgeBaseSkeleton />}><ProtectedRoute><KnowledgeBaseDetail /></ProtectedRoute></LazyRoute></RouteErrorBoundary>,
      },
      {
        path: "search",
        element: <RouteErrorBoundary><LazyRoute fallback={<SearchResultsSkeleton />}><ProtectedRoute><Search /></ProtectedRoute></LazyRoute></RouteErrorBoundary>,
      },
      {
        path: "read/:id",
        element: <RouteErrorBoundary><LazyRoute><ProtectedRoute><Read /></ProtectedRoute></LazyRoute></RouteErrorBoundary>,
      },
      {
        path: "read",
        element: <RouteErrorBoundary><LazyRoute><ProtectedRoute><Read /></ProtectedRoute></LazyRoute></RouteErrorBoundary>,
      },
      {
        path: "chat",
        element: <RouteErrorBoundary><LazyRoute><ProtectedRoute><Chat /></ProtectedRoute></LazyRoute></RouteErrorBoundary>,
      },
      {
        path: "settings",
        element: <RouteErrorBoundary><LazyRoute><ProtectedRoute><Settings /></ProtectedRoute></LazyRoute></RouteErrorBoundary>,
      },
      {
        path: "notes",
        element: <RouteErrorBoundary><LazyRoute fallback={<NotesSkeleton />}><ProtectedRoute><Notes /></ProtectedRoute></LazyRoute></RouteErrorBoundary>,
      },
      {
        path: "dashboard",
        element: <RouteErrorBoundary><LazyRoute><ProtectedRoute><Dashboard /></ProtectedRoute></LazyRoute></RouteErrorBoundary>,
      },
      {
        path: "analytics",
        element: <RouteErrorBoundary><LazyRoute fallback={<AnalyticsSkeleton />}><ProtectedRoute><Analytics /></ProtectedRoute></LazyRoute></RouteErrorBoundary>,
      },
      {
        path: "compare",
        element: <RouteErrorBoundary><LazyRoute><ProtectedRoute><Compare /></ProtectedRoute></LazyRoute></RouteErrorBoundary>,
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
]);
