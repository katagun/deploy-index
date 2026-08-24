// Loaded synchronously in <head> so the theme applies before first paint.
// Kept external so the Content-Security-Policy needs no 'unsafe-inline' grant.
(() => {
  let saved = null;
  try { saved = localStorage.getItem('deployindex-theme'); } catch (_error) { /* storage may be unavailable */ }
  const theme = saved || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  document.documentElement.dataset.theme = theme;
})();
