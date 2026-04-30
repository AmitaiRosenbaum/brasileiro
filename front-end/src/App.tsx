import { useEffect, useState } from "react";
import type { AxiosError } from "axios";
import {
  fetchCurrentUser,
  logoutUser,
  type AuthenticatedUser,
} from "./api/auth";
import Layout from "./Layout";
import AllSongsPage from "./pages/all-songs";
import LoadingPage from "./pages/loading";
import LoginPage from "./pages/login";
import MainPage from "./pages/main";
import SongDetailPage from "./pages/song-detail";
import { navigateTo, navigationEvent } from "./utils/navigation";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

function isProtectedPath(pathname: string) {
  return pathname === "/" || pathname.startsWith("/songs");
}

function App() {
  const [locationState, setLocationState] = useState({
    pathname: window.location.pathname,
    search: window.location.search,
  });
  const [authStatus, setAuthStatus] = useState<AuthStatus>("loading");
  const [currentUser, setCurrentUser] = useState<AuthenticatedUser | null>(
    null,
  );
  const { pathname, search } = locationState;

  useEffect(() => {
    const syncLocation = () =>
      setLocationState({
        pathname: window.location.pathname,
        search: window.location.search,
      });

    window.addEventListener("popstate", syncLocation);
    window.addEventListener(navigationEvent, syncLocation);

    return () => {
      window.removeEventListener("popstate", syncLocation);
      window.removeEventListener(navigationEvent, syncLocation);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function bootstrapSession() {
      try {
        const user = await fetchCurrentUser();

        if (cancelled) {
          return;
        }

        setCurrentUser(user);
        setAuthStatus("authenticated");
      } catch (error) {
        if (cancelled) {
          return;
        }

        const statusCode = (error as AxiosError).response?.status;
        setCurrentUser(null);

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

  const handleLogin = (user: AuthenticatedUser) => {
    setCurrentUser(user);
    setAuthStatus("authenticated");
    navigateTo("/", { replace: true });
  };

  const handleLogout = async () => {
    setAuthStatus("loading");

    try {
      await logoutUser();
    } catch (_error) {
      // Treat failed logout requests the same as a signed-out session.
    }

    setCurrentUser(null);
    setAuthStatus("unauthenticated");
    navigateTo("/login", { replace: true });
  };

  if (authStatus === "loading") {
    return <LoadingPage />;
  }

  if (authStatus === "unauthenticated") {
    return pathname === "/login" ? (
      <LoginPage onLogin={handleLogin} />
    ) : (
      <LoadingPage />
    );
  }

  const page =
    pathname === "/songs/view" ? (
      <SongDetailPage
        currentUser={currentUser}
        onLogout={handleLogout}
        search={search}
      />
    ) : pathname === "/songs" ? (
      <AllSongsPage currentUser={currentUser} onLogout={handleLogout} />
    ) : (
      <MainPage currentUser={currentUser} onLogout={handleLogout} />
    );

  return <Layout>{page}</Layout>;
}

export default App;
