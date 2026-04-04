import { RouterProvider } from "react-router";
import { router } from "./routes";
import { LanguageProvider } from "./contexts/LanguageContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { Toaster } from "react-hot-toast";
import { ErrorBoundary } from "./components/ErrorBoundary";

function App() {
  return (
    <ErrorBoundary>
      <Toaster position="top-right" />
      <LanguageProvider>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </LanguageProvider>
    </ErrorBoundary>
  );
}

export default App;