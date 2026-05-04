import type { SongType, SongVersionType } from "../../types/songs";
import { fetchCsrfToken } from "../auth";
import { axiosFetch, axiosPatch } from "../../utils/axios";
import useSWR, { mutate } from "swr";
import type { AllSongsType, ArtistType, SongURLType } from "../../types/songs";

const endpoints = {
  songUrl: "songs/getSongUrl",
  allSongs: "songs/getAllSongs",
  artists: "songs/artist/",
};

export type AllSongsParams = {
  id?: number;
  key?: string;
  mode?: "title" | "artist";
  page?: number;
  page_size?: number;
  search?: string;
  section?: string;
};

export function useSongUrl(song: SongType | SongVersionType | null) {
  const params = { id: song?.id };
  const { data, ...other } = useSWR(
    song == null ? null : [endpoints.songUrl, params],
    ([endpoint, params]) => axiosFetch<SongURLType>(endpoint, params),
    {
      revalidateOnFocus: false,
      revalidateIfStale: false,
      revalidateOnReconnect: false,
    },
  );

  return { data: data && (data.url as string), ...other };
}

export function useAllSongs(params?: AllSongsParams, enabled = true) {
  const { data, ...other } = useSWR(
    enabled ? [endpoints.allSongs, params ?? {}] : null,
    ([endpoint, params]) => axiosFetch<AllSongsType>(endpoint, params),
  );

  return { data: data && data.data, pagination: data?.pagination, ...other };
}

export function useSong(songId: number | null, songKey?: string | null) {
  const params = songId ? { id: songId } : songKey ? { key: songKey } : null;
  const { data, ...other } = useSWR(
    params ? [endpoints.allSongs, params] : null,
    ([endpoint, params]) => axiosFetch<AllSongsType>(endpoint, params),
  );

  return { data: data && data.data, ...other };
}

export function useSongSearch(search: string, limit = 8) {
  const trimmedSearch = search.trim();
  const { data, ...other } = useSWR(
    trimmedSearch
      ? [endpoints.allSongs, { search: trimmedSearch, page_size: limit }]
      : null,
    ([endpoint, params]) => axiosFetch<AllSongsType>(endpoint, params),
  );

  return { data: data?.data ?? [], ...other };
}

export function useArtists(enabled = true) {
  const { data, ...other } = useSWR(
    enabled ? endpoints.artists : null,
    (endpoint) => axiosFetch<ArtistType[]>(endpoint, {}),
  );

  return { data: data ?? [], ...other };
}

export type UpdateSongMetadataPayload = {
  title?: string;
  artist?: string;
};

export async function updateSongMetadata(
  songId: number,
  payload: UpdateSongMetadataPayload,
) {
  await fetchCsrfToken();
  const response = await axiosPatch<unknown, UpdateSongMetadataPayload>(
    `songs/${songId}/metadata`,
    payload,
  );
  await mutate((key) => Array.isArray(key) && key[0] === endpoints.allSongs);
  return response;
}
