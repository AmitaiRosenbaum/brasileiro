export const navigationEvent = "brasileiro:navigate";

export function navigateTo(pathname: string, options?: { replace?: boolean }) {
  if (options?.replace) {
    window.history.replaceState({}, "", pathname);
  } else {
    window.history.pushState({}, "", pathname);
  }

  window.dispatchEvent(new Event(navigationEvent));
}

export function navigateToSong(songId: number, versionId?: number) {
  const params = new URLSearchParams({ id: String(songId) });
  if (versionId != null) {
    params.set("version", String(versionId));
  }
  navigateTo(`/songs/view?${params.toString()}`);
}

export function navigateToBook(bookId: number) {
  navigateTo(`/books/view?id=${encodeURIComponent(String(bookId))}`);
}

export function navigateToPlaylist(playlistId: number) {
  navigateTo(`/playlists/view?id=${encodeURIComponent(String(playlistId))}`);
}
