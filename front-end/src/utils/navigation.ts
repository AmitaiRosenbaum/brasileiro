export const navigationEvent = "brasileiro:navigate";

export function navigateTo(pathname: string) {
  window.history.pushState({}, "", pathname);
  window.dispatchEvent(new Event(navigationEvent));
}
