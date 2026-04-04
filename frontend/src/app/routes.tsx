import { createBrowserRouter, Navigate } from "react-router";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/Login";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Library } from "./pages/Library";
import { Search } from "./pages/Search";
import { Read } from "./pages/Read";
import { Chat } from "./pages/Chat";
import { Upload } from "./pages/Upload";
import { Settings } from "./pages/Settings";
import { useAuth } from "@/contexts/AuthContext";

// Auth guard component for protected routes
// Uses AuthContext (Cookie-based auth) instead of localStorage
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  // Show loading state while checking auth
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          <span className="text-muted-foreground text-sm">Loading...</span>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
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
    // Layout is a wrapper for all app pages, no path needed
    element: <Layout />,
    children: [
      {
        path: "dashboard",
        element: <ProtectedRoute><Dashboard /></ProtectedRoute>,
      },
      {
        path: "library",
        element: <ProtectedRoute><Library /></ProtectedRoute>,
      },
      {
        path: "search",
        element: <ProtectedRoute><Search /></ProtectedRoute>,
      },
      {
        path: "read",
        element: <ProtectedRoute><Read /></ProtectedRoute>,
      },
      {
        path: "chat",
        element: <ProtectedRoute><Chat /></ProtectedRoute>,
      },
      {
        path: "upload",
        element: <ProtectedRoute><Upload /></ProtectedRoute>,
      },
      {
        path: "settings",
        element: <ProtectedRoute><Settings /></ProtectedRoute>,
      },
    ],
  },
]);