import { createBrowserRouter } from "react-router";
import { Landing } from "./pages/Landing";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Landing,
  },
  // Additional routes will be added in future plans:
  // - /login
  // - /dashboard
  // - /library
  // - /search
  // - /read
  // - /chat
  // - /upload
  // - /settings
]);