import type { Playlist } from "./auth";
import { fetchCsrfToken } from "./auth";
import { axiosDelete, axiosPatch, axiosPost } from "../utils/axios";

type CreatePlaylistRequest = {
  name: string;
  songs: number[];
};

type UpdatePlaylistRequest = Partial<CreatePlaylistRequest>;

export async function createPlaylist(payload: CreatePlaylistRequest) {
  await fetchCsrfToken();
  return axiosPost<Playlist, CreatePlaylistRequest>("playlists/", payload);
}

export async function updatePlaylist(
  playlistId: number,
  payload: UpdatePlaylistRequest,
) {
  await fetchCsrfToken();
  return axiosPatch<Playlist, UpdatePlaylistRequest>(
    `playlists/${playlistId}/`,
    payload,
  );
}

export async function deletePlaylist(playlistId: number) {
  await fetchCsrfToken();
  return axiosDelete<void>(`playlists/${playlistId}/`);
}

export async function sharePlaylist(playlistId: number, username: string) {
  await fetchCsrfToken();
  return axiosPost<Playlist, { username: string }>(
    `playlists/${playlistId}/members/`,
    { username },
  );
}

export async function removePlaylistMember(playlistId: number, userId: number) {
  await fetchCsrfToken();
  return axiosDelete<Playlist>(`playlists/${playlistId}/members/${userId}/`);
}
