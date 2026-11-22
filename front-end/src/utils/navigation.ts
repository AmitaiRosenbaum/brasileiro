import type { MouseEvent } from "react";

export const navigationEvent = "brasileiro:navigate";

export function navigateTo(pathname: string, options?: { replace?: boolean }) {
  if (options?.replace) {
    window.history.replaceState({}, "", pathname);
  } else {
    window.history.pushState({}, "", pathname);
  }

  window.dispatchEvent(new Event(navigationEvent));
}

export function handleInternalLinkClick(
  event: MouseEvent<HTMLElement>,
  pathname: string,
) {
  if (
    event.defaultPrevented ||
    event.button !== 0 ||
    event.ctrlKey ||
    event.metaKey ||
    event.shiftKey ||
    event.altKey
  ) {
    return;
  }

  event.preventDefault();
  navigateTo(pathname);
}

export function songPath(songId: number, versionId?: number) {
  const params = new URLSearchParams({ id: String(songId) });
  if (versionId != null) {
    params.set("version", String(versionId));
  }
  return `/songs/view?${params.toString()}`;
}

export function navigateToSong(songId: number, versionId?: number) {
  navigateTo(songPath(songId, versionId));
}

export function bookPath(bookId: number) {
  return `/books/view?id=${encodeURIComponent(String(bookId))}`;
}

export function navigateToBook(bookId: number) {
  navigateTo(bookPath(bookId));
}

export function artistPath(artistName: string) {
  return `/artists/view?name=${encodeURIComponent(artistName)}`;
}

export function navigateToArtist(artistName: string) {
  navigateTo(artistPath(artistName));
}

export function playlistPath(playlistId: number) {
  return `/playlists/view?id=${encodeURIComponent(String(playlistId))}`;
}

export function navigateToPlaylist(playlistId: number) {
  navigateTo(playlistPath(playlistId));
}
