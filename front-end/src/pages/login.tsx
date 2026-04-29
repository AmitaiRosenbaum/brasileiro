import { Alert, Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import type { AxiosError } from "axios";
import { useState, type FormEvent } from "react";
import { loginUser, type AuthenticatedUser } from "../api/auth";

type LoginPageProps = {
  onLogin: (user: AuthenticatedUser) => void;
};

function getErrorMessage(error: unknown) {
  const apiError = error as AxiosError<{ detail?: string }>;

  if (apiError.response?.data?.detail) {
    return apiError.response.data.detail;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "We couldn't sign you in with those credentials.";
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const user = await loginUser({
        username: username.trim(),
        password,
      });

      onLogin(user);
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        px: 2,
        background:
          "radial-gradient(circle at top left, rgba(20, 83, 45, 0.22), transparent 28%), radial-gradient(circle at bottom right, rgba(120, 53, 15, 0.16), transparent 24%), linear-gradient(145deg, #f7f3ed 0%, #eef4ee 46%, #f8efe7 100%)",
      }}
    >
      <Paper
        elevation={0}
        sx={{
          width: "100%",
          maxWidth: 460,
          p: { xs: 3, sm: 4 },
          borderRadius: 3,
          border: "1px solid rgba(87, 83, 78, 0.14)",
          bgcolor: "rgba(255, 255, 255, 0.88)",
          boxShadow: "0 24px 80px rgba(28, 25, 23, 0.10)",
          backdropFilter: "blur(10px)",
        }}
      >
        <Stack spacing={3}>
          <Stack spacing={1.5}>
            <Typography variant="overline" sx={{ color: "#14532d", fontWeight: 800 }}>
              Brasileiro
            </Typography>
            <Typography variant="h3" sx={{ fontWeight: 850, lineHeight: 0.95 }}>
              Sign in to the archive.
            </Typography>
            <Typography color="text.secondary">
              Use your account to search the collection and open protected scores.
            </Typography>
          </Stack>

          {errorMessage ? <Alert severity="error">{errorMessage}</Alert> : null}

          <Box component="form" onSubmit={handleSubmit}>
            <Stack spacing={2}>
              <TextField
                label="Username"
                name="username"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                fullWidth
              />
              <TextField
                label="Password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                fullWidth
              />
              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={isSubmitting}
                sx={{
                  mt: 1,
                  py: 1.4,
                  borderRadius: 999,
                  bgcolor: "#14532d",
                  fontWeight: 800,
                  "&:hover": {
                    bgcolor: "#0f3f22",
                  },
                }}
              >
                {isSubmitting ? "Signing in..." : "Sign in"}
              </Button>
            </Stack>
          </Box>
        </Stack>
      </Paper>
    </Box>
  );
}
