import { useEffect, useState } from "react";
import Layout from "./Layout";
import AllSongsPage from "./pages/all-songs";
import MainPage from "./pages/main";
import { navigationEvent } from "./utils/navigation";

function App() {
  const [pathname, setPathname] = useState(window.location.pathname);

  useEffect(() => {
    const syncPathname = () => setPathname(window.location.pathname);

    window.addEventListener("popstate", syncPathname);
    window.addEventListener(navigationEvent, syncPathname);

    return () => {
      window.removeEventListener("popstate", syncPathname);
      window.removeEventListener(navigationEvent, syncPathname);
    };
  }, []);

  return (
    <Layout>{pathname === "/songs" ? <AllSongsPage /> : <MainPage />}</Layout>
  );
}

export default App;
