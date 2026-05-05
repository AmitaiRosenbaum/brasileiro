import type { SongType, SongVersionType } from "../../types/songs";
import { fetchCsrfToken } from "../auth";
import { axiosFetch, axiosPatch } from "../../utils/axios";
import useSWR, { mutate, type SWRConfiguration } from "swr";
import type {
  AllSongsType,
  ArtistType,
  BookSongsType,
  BookType,
  SongURLType,
} from "../../types/songs";

const endpoints = {
  songUrl: "songs/getSongUrl",
  allSongs: "songs/getAllSongs",
  artists: "songs/artist/",
  books: "songs/books/",
};

export type AllSongsParams = {
  id?: number;
  key?: string;
  mode?: "title" | "artist";
  page?: number;
  page_size?: number;
  random?: boolean;
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

export function useSongUrls(songs: SongVersionType[]) {
  const songIds = songs.map((song) => song.id);
  const { data, ...other } = useSWR(
    songIds.length ? [endpoints.songUrl, songIds] : null,
    async ([endpoint, songIds]) => {
      const urls = await Promise.all(
        songIds.map(async (songId) => {
          const response = await axiosFetch<SongURLType>(endpoint, { id: songId });
          return [songId, response?.url] as const;
        }),
      );

      return Object.fromEntries(
        urls.filter((entry): entry is [number, string] => Boolean(entry[1])),
      );
    },
    {
      revalidateOnFocus: false,
      revalidateIfStale: false,
      revalidateOnReconnect: false,
    },
  );

  return { data: data ?? {}, ...other };
}

export function useAllSongs(
  params?: AllSongsParams,
  enabled = true,
  config?: SWRConfiguration,
) {
  const { data, ...other } = useSWR(
    enabled ? [endpoints.allSongs, params ?? {}] : null,
    ([endpoint, params]) => axiosFetch<AllSongsType>(endpoint, params),
    config,
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

export function useBooks(enabled = true) {
  const { data, ...other } = useSWR(
    enabled ? endpoints.books : null,
    (endpoint) => axiosFetch<BookType[]>(endpoint, {}),
  );

  return { data: data ?? [], ...other };
}

export function useBookSongs(bookId: number | null) {
  const { data, ...other } = useSWR(
    bookId ? [`songs/books/${bookId}/songs`, {}] : null,
    ([endpoint, params]) => axiosFetch<BookSongsType>(endpoint, params),
  );

  return { data: data?.data ?? [], book: data?.book, ...other };
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
