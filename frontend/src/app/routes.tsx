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

// Auth guard component for protected routes
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuth = localStorage.getItem('auth_token');
  return isAuth ? children : <Navigate to="/login" replace />;
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