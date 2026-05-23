/** Bridges tab chrome actions → community chat screen. */
type VoidFn = () => void;

let onSearchToggle: VoidFn | null = null;
let onMediaToggle: VoidFn | null = null;

export const chatChromeBridge = {
  setSearchHandler(handler: VoidFn | null) {
    onSearchToggle = handler;
  },
  setMediaHandler(handler: VoidFn | null) {
    onMediaToggle = handler;
  },
  toggleSearch() {
    onSearchToggle?.();
  },
  toggleMedia() {
    onMediaToggle?.();
  },
};
