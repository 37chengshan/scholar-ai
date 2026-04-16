import { RouterProvider } from "react-router";
import { router } from "./routes";
import { LanguageProvider } from "./contexts/LanguageContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { Toaster as SonnerToaster } from "sonner";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/lib/queryClient";

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <SonnerToaster position="top-right" richColors duration={3000} />
        <LanguageProvider>
          <AuthProvider>
            <RouterProvider router={router} />
          </AuthProvider>
        </LanguageProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
