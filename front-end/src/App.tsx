import { useEffect, useState } from "react";
import type { AxiosError } from "axios";
import { fetchCurrentUser } from "./api/auth";
import Layout from "./Layout";
import AllSongsPage from "./pages/all-songs";
import LoadingPage from "./pages/loading";
import LoginPage from "./pages/login";
import MainPage from "./pages/main";
import { navigateTo, navigationEvent } from "./utils/navigation";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

const protectedPaths = new Set(["/", "/songs"]);

function isProtectedPath(pathname: string) {
  return protectedPaths.has(pathname);
}

function App() {
  const [pathname, setPathname] = useState(window.location.pathname);
  const [authStatus, setAuthStatus] = useState<AuthStatus>("loading");

  useEffect(() => {
    const syncPathname = () => setPathname(window.location.pathname);

    window.addEventListener("popstate", syncPathname);
    window.addEventListener(navigationEvent, syncPathname);

    return () => {
      window.removeEventListener("popstate", syncPathname);
      window.removeEventListener(navigationEvent, syncPathname);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function bootstrapSession() {
      try {
        await fetchCurrentUser();

        if (cancelled) {
          return;
        }

        setAuthStatus("authenticated");
      } catch (error) {
        if (cancelled) {
          return;
        }

        const statusCode = (error as AxiosError).response?.status;

        if (statusCode === 401 || statusCode === 403) {
          setAuthStatus("unauthenticated");
          return;
        }

        setAuthStatus("unauthenticated");
      }
    }

    bootstrapSession();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (authStatus === "loading") {
      return;
    }

    if (authStatus === "unauthenticated" && isProtectedPath(pathname)) {
      navigateTo("/login", { replace: true });
      return;
    }

    if (authStatus === "authenticated" && pathname === "/login") {
      navigateTo("/", { replace: true });
    }
  }, [authStatus, pathname]);

  const handleLogin = () => {
    setAuthStatus("authenticated");
    navigateTo("/", { replace: true });
  };

  if (authStatus === "loading") {
    return <LoadingPage />;
  }

  if (authStatus === "unauthenticated") {
    return pathname === "/login" ? <LoginPage onLogin={handleLogin} /> : <LoadingPage />;
  }

  const page = pathname === "/songs" ? <AllSongsPage /> : <MainPage />;

  return <Layout>{page}</Layout>;
}

export default App;
