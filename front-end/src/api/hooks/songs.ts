import type { SongType, SongVersionType } from "../../types/songs";
import { axiosFetch } from "../../utils/axios";
import useSWR from "swr";
import type { AllSongsType, SongURLType } from "../../types/songs";

const endpoints = {
  songUrl: "songs/getSongUrl",
  allSongs: "songs/getAllSongs",
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

export function useAllSongs(params?: AllSongsParams) {
  const { data, ...other } = useSWR(
    [endpoints.allSongs, params ?? {}],
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
