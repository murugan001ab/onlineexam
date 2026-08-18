import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { router } from "@/routes/router";
import { useAuthStore } from "@/store/authStore";
import { FullScreenLoader } from "@/components/ui/Spinner";

function App() {
  const hydrate = useAuthStore((s) => s.hydrate);
  const status = useAuthStore((s) => s.status);

  useEffect(() => {
    hydrate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (status === "idle") {
    return <FullScreenLoader label="Starting up..." />;
  }

  return (
    <>
      <RouterProvider router={router} />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "rgba(13, 13, 33, 0.9)",
            color: "#f1f5f9",
            border: "1px solid rgba(255,255,255,0.1)",
            backdropFilter: "blur(12px)",
          },
          success: { iconTheme: { primary: "#8b5cf6", secondary: "#fff" } },
          error: { iconTheme: { primary: "#f43f5e", secondary: "#fff" } },
        }}
      />
    </>
  );
}

export default App;
