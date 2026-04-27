import { Link } from "@mui/material";
import type React from "react";
import { navigateTo } from "../utils/navigation";

export default function Footer() {
  const handleClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    navigateTo("/songs");
  };

  return (
    <Link color="inherit" underline="hover" href="/songs" onClick={handleClick}>
      All Songs A-Z
    </Link>
  );
}
