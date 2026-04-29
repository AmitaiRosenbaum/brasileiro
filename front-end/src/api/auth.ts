import axiosService, { axiosPost, setCsrfToken } from "../utils/axios";

export type AuthenticatedUser = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
};

type CsrfResponse = {
  csrfToken: string;
};

type LoginRequest = {
  username: string;
  password: string;
};

type LoginResponse = {
  user: AuthenticatedUser;
  csrfToken: string;
};

type CurrentUserResponse = {
  user: AuthenticatedUser;
};

export async function fetchCsrfToken() {
  const response = await axiosService.get<CsrfResponse>("auth/csrf/");
  setCsrfToken(response.data.csrfToken);
  return response.data.csrfToken;
}

export async function fetchCurrentUser() {
  const response = await axiosService.get<CurrentUserResponse>("auth/me/");
  return response.data.user;
}

export async function loginUser(credentials: LoginRequest) {
  if (!credentials.username || !credentials.password) {
    throw new Error("Username and password are required.");
  }

  if (!credentials.username.trim() || !credentials.password.trim()) {
    throw new Error("Username and password are required.");
  }

  await fetchCsrfToken();
  const response = await axiosPost<LoginResponse, LoginRequest>("auth/login/", credentials);
  setCsrfToken(response.csrfToken);
  return response.user;
}
