import { Box, Link, Stack, Typography } from "@mui/material";
import { handleInternalLinkClick } from "../utils/navigation";

type AppBrandProps = {
  compact?: boolean;
};

export default function AppBrand({ compact = false }: AppBrandProps) {
  return (
    <Link
      color="inherit"
      underline="none"
      href="/"
      onClick={(event) => handleInternalLinkClick(event, "/")}
      sx={{
        display: "inline-flex",
        borderRadius: 2,
        color: "inherit",
      }}
    >
      <Stack direction="row" alignItems="center" spacing={1.5}>
        <Box
          component="img"
          src="/icon.svg"
          alt=""
          sx={{
            width: compact ? 34 : 36,
            height: compact ? 34 : 36,
            color: "#14532d",
            p: 1,
            borderRadius: 2,
            bgcolor: "#ffffff",
            boxShadow: "0 10px 30px rgba(28, 25, 23, 0.08)",
          }}
        />
        <Typography
          variant="h6"
          sx={{
            fontWeight: 800,
            letterSpacing: "-0.02em",
          }}
        >
          Brasileiro
        </Typography>
      </Stack>
    </Link>
  );
}
