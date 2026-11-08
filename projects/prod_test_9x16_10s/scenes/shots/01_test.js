// scenes/shots/01_test.js — minimal, self-contained 9:16 verification shot.
// Uses only registerShot + raw canvas (no project-specific sets/cast) so it has no external deps.
import { E, registerShot } from '/engine/core.js';

registerShot('s001', { draw(g, t) {
  // background vertical gradient
  const grad = g.createLinearGradient(0, 0, 0, E.H);
  grad.addColorStop(0, '#1a1030');
  grad.addColorStop(1, '#3a1d4d');
  g.fillStyle = grad;
  g.fillRect(0, 0, E.W, E.H);

  // subtle camera push (z from 1.0 -> 1.06) implemented as a scale of the scene
  const z = 1 + 0.06 * (t / 10);
  g.save();
  g.translate(E.W / 2, E.H / 2);
  g.scale(z, z);
  g.translate(-E.W / 2, -E.H / 2);

  // animated orb that bobs around the upper third
  const cx = E.W / 2 + Math.sin(t * 1.1) * 180;
  const cy = E.H * 0.36 + Math.cos(t * 1.4) * 130;
  const r = 70 + 16 * Math.sin(t * 2.0);
  const og = g.createRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 0.2, cx, cy, r);
  og.addColorStop(0, '#fff3c4');
  og.addColorStop(1, '#ff9b3d');
  g.fillStyle = og;
  g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2); g.fill();

  // ground line + soft shadow
  const gy = E.H * 0.72;
  g.fillStyle = 'rgba(0,0,0,0.25)';
  g.beginPath(); g.ellipse(cx, gy + 10, r * 1.1, 16, 0, 0, Math.PI * 2); g.fill();
  g.fillStyle = '#0d0820';
  g.fillRect(0, gy, E.W, E.H - gy);

  g.restore();

  // HUD text (deterministic; no random/Date.now)
  g.fillStyle = '#ffffff';
  g.textAlign = 'center';
  g.font = '900 54px sans-serif';
  g.fillText('PROD TEST 9:16', E.W / 2, E.H * 0.86);
  g.font = '800 34px sans-serif';
  g.fillText('frame ' + Math.round(t * E.fps) + ' / ' + Math.round(E.fps * 10), E.W / 2, E.H * 0.92);
}});
