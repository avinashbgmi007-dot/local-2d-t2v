// cast.js — the two leads. Colour AND marker are fixed here and only here; a shot that declares
// its own copy of a character is how a series drifts.
// Markers are never a colour difference: body colour comes from the style theme, so a theme swap
// would otherwise change who a character is. See chars/markers.js for the two allowed forms.
export const RAE = { color: '#2f9e8f', marker: 'bob' };       // silhouette: hair past the shoulders
export const NILS = { color: '#c2553d', marker: 'glasses' };  // detail: round wire spectacles
export const CAST = [RAE, NILS];
