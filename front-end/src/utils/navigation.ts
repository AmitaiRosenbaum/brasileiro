export const navigationEvent = "brasileiro:navigate";

export function navigateTo(pathname: string, options?: { replace?: boolean }) {
  if (options?.replace) {
    window.history.replaceState({}, "", pathname);
  } else {
    window.history.pushState({}, "", pathname);
  }

  window.dispatchEvent(new Event(navigationEvent));
}

export function navigateToSong(songKey: string) {
  navigateTo(`/songs/view?key=${encodeURIComponent(songKey)}`);
}

export function navigateToPlaylist(playlistId: number) {
  navigateTo(`/playlists/view?id=${encodeURIComponent(String(playlistId))}`);
}
