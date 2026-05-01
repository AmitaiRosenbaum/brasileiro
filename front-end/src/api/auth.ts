import axiosService, { axiosPost, setCsrfToken } from "../utils/axios";

export type Playlist = {
  id: number;
  name: string;
  songs: number[];
  is_liked_songs: boolean;
};

export type AuthenticatedUser = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  playlists: Playlist[];
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

type CurrentUserUpdateRequest = {
  email?: string;
  first_name?: string;
  last_name?: string;
};

function normalizeUser(user: AuthenticatedUser): AuthenticatedUser {
  return {
    ...user,
    playlists: Array.isArray(user.playlists)
      ? user.playlists.map((playlist) => ({
          ...playlist,
          songs: Array.isArray(playlist.songs) ? playlist.songs : [],
        }))
      : [],
  };
}

export async function fetchCsrfToken() {
  const response = await axiosService.get<CsrfResponse>("auth/csrf/");
  setCsrfToken(response.data.csrfToken);
  return response.data.csrfToken;
}

export async function fetchCurrentUser() {
  const response = await axiosService.get<CurrentUserResponse>("auth/me/");
  return normalizeUser(response.data.user);
}

export async function updateCurrentUser(payload: CurrentUserUpdateRequest) {
  const csrfToken = await fetchCsrfToken();
  const response = await axiosService.patch<CurrentUserResponse>("auth/me/", payload, {
    headers: {
      "X-CSRFToken": csrfToken,
    },
  });
  return normalizeUser(response.data.user);
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
  return normalizeUser(response.user);
}

export async function logoutUser() {
  await fetchCsrfToken();
  await axiosPost<void, Record<string, never>>("auth/logout/", {});
  setCsrfToken(null);
}
