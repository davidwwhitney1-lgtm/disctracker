// track.js - rebuilds a throw's motion from the disc's raw readings, past what the sensor can measure.
//
// The disc's IMU tops out at 16 g and 2294 deg/s (382 rpm); a hard throw passes both. Speed is the hand's force added
// up over the pull, so force cut off at 16 g makes it read low (21 % at a 40 g peak, 46 % at 60 g, on simulated
// throws). Rebuilt here:
//  - the cut-off force: the pull's push, fitted as a size and a direction that each change smoothly (in a frame that
//    does not turn with the disc's spin) to every reading the sensor did get; a maxed axis only says "16 g or more".
//    As the disc turns, the push swings from one axis to the other, so the axis that is not maxed keeps seeing it.
//  - the spin while the gyro is maxed: a curve that only rises, from its last reading to the flight's spin; its shape
//    comes from the force fit when one shape fits clearly better.
//  - the release: where the readings settle to the flight's steady force (the disc's own point can come early).
//  - the flight's spin from the off-centre sensor's steady force when the gyro is maxed (w = sqrt(a / r)).
//  - the chip's real clock (418.6/s, not 416), repeated samples, and the off-centre sensor's own spin force taken
//    out of every reading (not once at the end).
// 270 simulated throws (dtbuild/track/bench.js), the fast ones (45 mph and up): speed off by 1.7 mph typically (the
// disc's maths: 14), 6 mph at the 90th percentile (29); direction 1.0 deg (6.3).
(function (G) {
"use strict";
const D2R = Math.PI / 180, R2D = 180 / Math.PI, GMS = 9.80665, TAU = 2 * Math.PI, MPH = 2.2369363;
const GSAT = 32200, ASAT = 32700;                           // raw counts at or past these: maxed out
const AMAX = 32767 * 0.000488 * GMS;                       // the accelerometer's top, m/s^2

const qmul = (a, b) => [a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3], a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
                        a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1], a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0]];
const qnorm = q => { const n = Math.hypot(q[0], q[1], q[2], q[3]); return [q[0] / n, q[1] / n, q[2] / n, q[3] / n]; };
const qrot = (q, v) => {
  const [w, x, y, z] = q, tx = 2 * (y * v[2] - z * v[1]), ty = 2 * (z * v[0] - x * v[2]), tz = 2 * (x * v[1] - y * v[0]);
  return [v[0] + w * tx + (y * tz - z * ty), v[1] + w * ty + (z * tx - x * tz), v[2] + w * tz + (x * ty - y * tx)];
};
const qexp = (w, dt) => { const n = Math.hypot(w[0], w[1], w[2]), a = 0.5 * n * dt; if (n < 1e-12) return [1, 0, 0, 0]; const s = Math.sin(a) / n; return [Math.cos(a), w[0] * s, w[1] * s, w[2] * s]; };
const fromUp = (ax, ay, az) => {                            // as Quat::fromUpVector in throw_metrics.h
  const n = Math.hypot(ax, ay, az); if (n < 1e-6) return [1, 0, 0, 0];
  ax /= n; ay /= n; az /= n; const wq = 1 + az;
  return wq < 1e-6 ? [0, 1, 0, 0] : qnorm([wq, ay, -ax, 0]);
};
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
function sixFrom(q, v, ccw) {                               // the six numbers' angle definitions (throw_metrics.h)
  const horiz = Math.hypot(v[0], v[1]), launch = Math.atan2(v[2], horiz) * R2D, n = qrot(q, [0, 0, 1]);
  let hyzer, nose;
  if (horiz > 0.5) {
    const fx = v[0] / horiz, fy = v[1] / horiz, lx = -fy, ly = fx;
    hyzer = Math.atan2(-(n[0] * lx + n[1] * ly), n[2]) * R2D;
    nose = Math.atan2(-(n[0] * fx + n[1] * fy), n[2]) * R2D - launch;
  } else { hyzer = Math.atan2(-n[1], n[2]) * R2D; nose = Math.atan2(-n[0], n[2]) * R2D; }
  if (!ccw) hyzer = -hyzer;
  return { speed: Math.hypot(v[0], v[1], v[2]) * MPH, launch, hyzer, nose };
}
function relHeading(q0, v) {
  const x0 = qrot(q0, [1, 0, 0]); let d = (Math.atan2(v[1], v[0]) - Math.atan2(x0[1], x0[0])) * R2D;
  while (d > 180) d -= 360; while (d < -180) d += 360; return d;
}

// Solve the symmetric positive system A x = b (Cholesky). A is an array of rows.
function cholSolve(A, b) {
  const n = b.length, L = A.map(r => r.slice());
  for (let j = 0; j < n; j++) {
    let d = L[j][j]; for (let k = 0; k < j; k++) d -= L[j][k] * L[j][k];
    if (d <= 1e-12) d = 1e-12; L[j][j] = Math.sqrt(d);
    for (let i = j + 1; i < n; i++) { let s = L[i][j]; for (let k = 0; k < j; k++) s -= L[i][k] * L[j][k]; L[i][j] = s / L[j][j]; }
  }
  const y = new Array(n);
  for (let i = 0; i < n; i++) { let s = b[i]; for (let k = 0; k < i; k++) s -= L[i][k] * y[k]; y[i] = s / L[i][i]; }
  const x = new Array(n);
  for (let i = n - 1; i >= 0; i--) { let s = y[i]; for (let k = i + 1; k < n; k++) s -= L[k][i] * x[k]; x[i] = s / L[i][i]; }
  return x;
}

// ---------------------------------------------------------------- the pull's force, fitted through the cut-off parts
// In the window [w0, w1): the in-plane reading z_k (complex, m/s^2) = e^{-i th_k} W(t_k) + B_k, where th = the disc's
// turn about its own axis since w0, W = the in-plane force in that non-turning frame (a smooth spline: hat functions
// every `dk` samples, kept smooth by a penalty on its bends) and B = the off-centre sensor's own spin force (known).
// Readings an axis didn't max out are matched; maxed ones must be at least the 16 g the sensor stopped at.
function fitPullForce(ax, ay, clipX, clipY, ok, th, B, w0, w1, dk, smooth) {
  const nk = Math.ceil((w1 - 1 - w0) / dk) + 1, nu = 2 * nk;
  const rows = [];                                         // {k, comp (0 x, 1 y), target, active (for maxed ones), sign}
  for (let k = w0; k < w1; k++) {
    if (!ok[k]) continue;
    for (const comp of [0, 1]) {
      const meas = comp ? ay[k] : ax[k], clipped = comp ? clipY[k] : clipX[k];
      rows.push({ k, comp, meas, clipped, sign: clipped ? Math.sign(meas) : 0, active: true });
    }
  }
  const basis = k => { const u = (k - w0) / dk, j = Math.min(nk - 2, Math.floor(u)), f = u - j; return [[j, 1 - f], [j + 1, f]]; };
  const rowCoef = (k, comp) => {                           // the reading's model, as coefficients on [Wr_j, Wi_j]
    const c = Math.cos(th[k - w0]), s = Math.sin(th[k - w0]), out = [];
    for (const [j, h] of basis(k)) {
      if (h === 0) continue;
      if (!comp) out.push([2 * j, h * c], [2 * j + 1, h * s]);          // Re(e^{-i th} W) = Wr cos + Wi sin
      else out.push([2 * j, -h * s], [2 * j + 1, h * c]);               // Im(e^{-i th} W) = -Wr sin + Wi cos
    }
    return out;
  };
  // Maxed readings are one-sided: the true value is somewhere past 16 g. Each counts only while the fit sits below
  // 16 g there (then it pulls the fit up to 16 g); re-solve until that set stops changing.
  let W = null;
  for (let it = 0; it < 20; it++) {
    const A = Array.from({ length: nu }, () => new Array(nu).fill(0)), b = new Array(nu).fill(0);
    for (const r of rows) {
      if (!r.active) continue;
      const co = rowCoef(r.k, r.comp), Bc = r.comp ? B[r.k - w0][1] : B[r.k - w0][0];
      const target = (r.clipped ? r.sign * AMAX : r.meas) - Bc, wgt = r.clipped ? 100 : 1;
      for (const [i, vi] of co) { b[i] += wgt * vi * target; for (const [j, vj] of co) A[i][j] += wgt * vi * vj; }
    }
    for (let j = 1; j < nk - 1; j++) for (const o of [0, 1]) {   // smoothness: second differences of W
      const idx = [2 * (j - 1) + o, 2 * j + o, 2 * (j + 1) + o], cf = [1, -2, 1];
      for (let a = 0; a < 3; a++) for (let c = 0; c < 3; c++) A[idx[a]][idx[c]] += smooth * cf[a] * cf[c];
    }
    for (let i = 0; i < nu; i++) A[i][i] += 1e-6;
    W = cholSolve(A, b);
    let changed = 0;
    for (const r of rows) {
      if (!r.clipped) continue;
      let m = 0; for (const [i, v] of rowCoef(r.k, r.comp)) m += v * W[i];
      m += r.comp ? B[r.k - w0][1] : B[r.k - w0][0];
      const act = r.sign * m < AMAX;
      if (act !== r.active) { r.active = act; changed++; }
    }
    if (!changed) break;
  }
  const model = (k, comp) => { let m = 0; for (const [i, v] of rowCoef(k, comp)) m += v * W[i]; return m + (comp ? B[k - w0][1] : B[k - w0][0]); };
  return { W, nk, model, rows, basis };
}

// The same readings, with the force as a size and a direction that are each smooth on their own: a push that grows
// and fades while it turns at a steady rate. (Smooth x and y parts would make a turning push cost "bend", so a missing
// part would come out short.) Started from the plain fit; Levenberg-Marquardt, with the same one-sided maxed readings.
function fitPolar(th, B, w0, cart, sM, sP) {
  const { nk, basis, rows } = cart, np = 2 * nk, x = new Array(np);
  let prev = null;
  for (let j = 0; j < nk; j++) {
    const wr = cart.W[2 * j], wi = cart.W[2 * j + 1];
    let a = Math.atan2(wi, wr);
    if (prev != null) { while (a - prev > Math.PI) a -= TAU; while (a - prev < -Math.PI) a += TAU; }
    x[j] = Math.hypot(wr, wi); x[nk + j] = a; prev = a;
  }
  const at = (k, x) => {
    let M = 0, P = 0; const hs = basis(k);
    for (const [j, h] of hs) { M += h * x[j]; P += h * x[nk + j]; }
    const ang = P - th[k - w0];
    return { M, c: Math.cos(ang), s: Math.sin(ang), hs };
  };
  const value = (k, comp, x) => { const e = at(k, x); return (comp ? e.M * e.s : e.M * e.c) + B[k - w0][comp]; };
  const cost = x => {
    let c = 0;
    for (const r of rows) {
      const m = value(r.k, r.comp, x);
      if (!r.clipped) c += (m - r.meas) ** 2;
      else if (r.sign * m < AMAX) c += 100 * (m - r.sign * AMAX) ** 2;
    }
    for (let j = 1; j < nk - 1; j++) c += sM * (x[j - 1] - 2 * x[j] + x[j + 1]) ** 2 + sP * (x[nk + j - 1] - 2 * x[nk + j] + x[nk + j + 1]) ** 2;
    return c;
  };
  let mu = 1e-3, cur = cost(x);
  for (let it = 0; it < 40; it++) {
    const H = Array.from({ length: np }, () => new Array(np).fill(0)), g = new Array(np).fill(0);
    for (const r of rows) {
      const e = at(r.k, x), m = (r.comp ? e.M * e.s : e.M * e.c) + B[r.k - w0][r.comp];
      let res, wgt;
      if (!r.clipped) { res = m - r.meas; wgt = 1; }
      else if (r.sign * m < AMAX) { res = m - r.sign * AMAX; wgt = 100; }
      else continue;
      const J = [];
      for (const [j, h] of e.hs) {
        if (!h) continue;
        J.push([j, h * (r.comp ? e.s : e.c)], [nk + j, h * (r.comp ? e.M * e.c : -e.M * e.s)]);
      }
      for (const [i, vi] of J) { g[i] += wgt * vi * res; for (const [j, vj] of J) H[i][j] += wgt * vi * vj; }
    }
    for (let j = 1; j < nk - 1; j++) for (const [o, sw] of [[0, sM], [nk, sP]]) {
      const idx = [o + j - 1, o + j, o + j + 1], cf = [1, -2, 1], d2 = x[idx[0]] - 2 * x[idx[1]] + x[idx[2]];
      for (let a = 0; a < 3; a++) { g[idx[a]] += sw * cf[a] * d2; for (let c = 0; c < 3; c++) H[idx[a]][idx[c]] += sw * cf[a] * cf[c]; }
    }
    let improved = false;
    for (let tries = 0; tries < 8 && !improved; tries++) {
      const A = H.map((row, i) => row.map((v, j) => i === j ? v * (1 + mu) + 1e-9 : v));
      const d = cholSolve(A, g.map(v => -v)), xn = x.map((v, i) => v + d[i]), cn = cost(xn);
      if (cn < cur) { for (let i = 0; i < np; i++) x[i] = xn[i]; const rel = (cur - cn) / cur; cur = cn; mu = Math.max(1e-6, mu / 3); improved = true; if (rel < 1e-7) it = 99; }
      else mu *= 4;
    }
    if (!improved) break;
  }
  return { x, nk, model: (k, comp) => value(k, comp, x), at: k => at(k, x), cost: cur };
}

// ---------------------------------------------------------------- release, end of flight, spin in flight
const median = arr => { const v = Array.from(arr).sort((x, y) => x - y), m = v.length >> 1; return v.length % 2 ? v[m] : 0.5 * (v[m - 1] + v[m]); };
// In free flight the in-plane readings are steady: the off-centre sensor's own spin force (w^2 r, fixed in the disc)
// plus a little air force turning with the spin. In the hand the pull swings round the disc as it spins up - many g.
// So the hand is done where they settle: 12 readings within 4 g of their middle value (and up/down within 5 g), none
// on the 16 g rail - a pull. (Only if that never happens: one axis clear and settled, the other on the rail, as the
// spin force alone can put it past ~1250 rpm.) And the spin has stopped climbing (in the hand it is still being spun
// up): steady where the gyro sees it, and not going past the gyro's top during those 12 readings. Then the last of
// the hand's gentle force is skipped: on a slow spin (the gyro not maxed), readings still off the flight's steady
// values by more than its own spread (at least 1.2 g); on a fast one, the last jump from one reading to the next
// bigger than 3 x the flight's own (at least 0.25 g) - the hand's force swings round with the spin, the flight's
// barely moves (its values drift with the wobble, so the first test would mislead there). The search
// starts where the spin passes 300 rpm (a throw spinning that fast leaves the hand within a few hundredths of a
// second) or 80 % of its fastest, whichever comes first. Returns -1 if nothing settles.
function findRelease(ax, ay, az, gzDps, satG, clipX, clipY, trig, n) {
  const M = 12, T = 4 * GMS, TZ = 5 * GMS;
  let top = 0; for (let k = trig; k < n; k++) top = Math.max(top, satG[k] ? 1e9 : Math.abs(gzDps[k]));
  const goal = Math.min(1800, 0.8 * top);
  let k0 = trig; for (let k = Math.max(0, trig - 60); k < n; k++) if (satG[k] || Math.abs(gzDps[k]) >= goal) { k0 = k; break; }
  const settled = (k, rail) => {
    let cx = 0, cy = 0, cg = 0;
    for (let j = k; j < k + M; j++) { cx += clipX[j]; cy += clipY[j]; cg += satG[j]; }
    if (rail ? (cx && cy) || cg < M : cx || cy) return false;
    const xs = ax.subarray(k, k + M), ys = ay.subarray(k, k + M), zs = az.subarray(k, k + M);
    const mx = cx ? 0 : median(xs), my = cy ? 0 : median(ys), mz = median(zs);
    for (let j = 0; j < M; j++) if (Math.hypot(cx ? 0 : xs[j] - mx, cy ? 0 : ys[j] - my) > T || Math.abs(zs[j] - mz) > TZ) return false;
    if (cg && cg < M) return false;                          // the spin went past the gyro's top just now: still spinning up
    if (!cg) {                                               // the gyro sees the spin: steady, one way
      let lo = 1e9, hi = 0, pos = 0;
      for (let j = k; j < k + M; j++) { const a = Math.abs(gzDps[j]); lo = Math.min(lo, a); hi = Math.max(hi, a); if (gzDps[j] > 0) pos++; }
      if ((pos && pos < M) || hi - lo > Math.max(60, 0.08 * hi)) return false;
    }
    return true;
  };
  for (const rail of [false, true]) for (let k = Math.max(0, k0 - 5); k + M <= n; k++) {
    if (!settled(k, rail)) continue;
    const a = k + 6, b = Math.min(n, a + M);
    if (rail || b - a < 6) return k;
    if (satG[k]) {
      const jump = j => Math.hypot(ax[j] - ax[j - 1], ay[j] - ay[j - 1]);
      const lj = Math.max(0.25 * GMS, 3 * median(Array.from({ length: b - a }, (_, i) => jump(a + i))));
      let last = k; for (let j = Math.max(1, k - 3); j < a; j++) if (jump(j) > lj) last = j;
      return last;
    }
    const mx = median(ax.subarray(a, b)), my = median(ay.subarray(a, b)), dev = j => Math.hypot(ax[j] - mx, ay[j] - my);
    const spread = median(Array.from({ length: b - a }, (_, i) => dev(a + i))), lim = Math.max(1.2 * GMS, 4 * spread);
    let last = k - 1; for (let j = k; j < a; j++) if (dev(j) > lim) last = j;
    return last + 1;
  }
  return -1;
}
// The end of the flight: the first reading after the release that jumps 5 g from the flight's steady values (the
// net, a catch, the ground).
function findImpact(ax, ay, az, rel, n) {
  const M = 12; if (rel + M >= n) return n;
  const mx = median(ax.subarray(rel, rel + M)), my = median(ay.subarray(rel, rel + M)), mz = median(az.subarray(rel, rel + M));
  for (let k = rel + M; k < n; k++) if (Math.hypot(ax[k] - mx, ay[k] - my) > 5 * GMS || Math.abs(az[k] - mz) > 5 * GMS) return k;
  return n;
}
// A wobbling disc's in-plane turning rate (gyro x and y, which don't max out) turns round, in the disc's own axes, at
// (I3 - I1) / I1 x its spin - about 0.93 x for a golf disc, whose axial moment of inertia is ~1.93 x its cross one -
// whatever the spin, so it measures the spin while the gyro's spin axis is maxed. Its rate of change turns the same
// way round zero, so the angle of that, unwrapped, against time gives the rate without needing the circle's centre
// (which a sensor a degree off the spin axis shifts). Returns {w (rad/s), n, rms (rad), mag, turns} or null.
function turnRate(xs, ys, dt) {
  const t = [], ph = [];
  let prev = null, off = 0, mag = 0;
  for (let i = 2; i < xs.length - 2; i++) {
    const dx = (xs[i + 2] - xs[i - 2]) / (4 * dt), dy = (ys[i + 2] - ys[i - 2]) / (4 * dt);
    mag += Math.hypot(dx, dy);
    let a = Math.atan2(dy, dx) + off;
    if (prev != null) { while (a - prev > Math.PI) { a -= TAU; off -= TAU; } while (a - prev < -Math.PI) { a += TAU; off += TAU; } }
    prev = a; t.push(i * dt); ph.push(a);
  }
  const N = t.length; if (N < 10) return null;
  let st = 0, sp = 0, stt = 0, stp = 0;
  for (let i = 0; i < N; i++) { st += t[i]; sp += ph[i]; stt += t[i] * t[i]; stp += t[i] * ph[i]; }
  const den = N * stt - st * st; if (den <= 0) return null;
  const w = (N * stp - st * sp) / den, b = (sp - w * st) / N;
  let ss = 0; for (let i = 0; i < N; i++) ss += (ph[i] - (b + w * t[i])) ** 2;
  return { w, n: N, rms: Math.sqrt(ss / N), mag: mag / N, turns: Math.abs(w) * (t[N - 1] - t[0]) / TAU };
}

// ---------------------------------------------------------------- the whole throw
// S: raw counts (n x 6, disc axes) of a capture; I: {alsb, glsb, bias (disc axes, deg/s), radius (m), rate (measured,
// samples/s) or odr}; o: {iRel (release index - the disc's own), spinRpm (the disc's flight spin, for the gyro's
// maxed stretch), trig (trigger index, default 415), old (true = the disc's current maths, for comparison)}.
function reconstruct(S, I, o = {}) {
  const n = S.length / 6, old = !!o.old, info0 = {};
  const dt = old ? 1 / 416 : 1 / (I.rate > 380 && I.rate < 460 ? I.rate : (I.odr || 416));
  const GL = I.glsb, AL = I.alsb;
  const gx = new Float64Array(n), gy = new Float64Array(n), gz = new Float64Array(n);
  const ax = new Float64Array(n), ay = new Float64Array(n), az = new Float64Array(n);
  const satG = new Uint8Array(n), clipX = new Uint8Array(n), clipY = new Uint8Array(n), clipZ = new Uint8Array(n), dup = new Uint8Array(n);
  for (let k = 0; k < n; k++) {
    const c = S.subarray(k * 6, k * 6 + 6);
    gx[k] = c[0] * GL; gy[k] = c[1] * GL; gz[k] = c[2] * GL;
    ax[k] = c[3] * AL * GMS; ay[k] = c[4] * AL * GMS; az[k] = c[5] * AL * GMS;
    if (!o.noClip && !o.noClipG) satG[k] = Math.abs(c[2]) >= GSAT ? 1 : 0;      // noClip*: tests with an unlimited sensor
    if (!o.noClip && !o.noClipA) { clipX[k] = Math.abs(c[3]) >= ASAT ? 1 : 0; clipY[k] = Math.abs(c[4]) >= ASAT ? 1 : 0; clipZ[k] = Math.abs(c[5]) >= ASAT ? 1 : 0; }
    if (k && c.every((v, j) => v === S[(k - 1) * 6 + j])) dup[k] = 1;
  }
  // A repeated sample stands for one that was lost (a FIFO slip, or a Bluetooth gap filled with copies): a straight
  // line from the sample before the run to the one after it. Maxed readings stay maxed.
  if (!old) for (let k = 1; k < n - 1; k++) {
    if (!dup[k]) continue;
    let e = k; while (e + 1 < n - 1 && dup[e + 1]) e++;
    const a = k - 1, b = e + 1;
    for (const [arr, cl] of [[gx, null], [gy, null], [gz, satG], [ax, clipX], [ay, clipY], [az, clipZ]])
      for (let j = k; j <= e; j++) {
        if (cl && (cl[a] || cl[b])) { cl[j] = 1; continue; }
        arr[j] = arr[a] + (arr[b] - arr[a]) * (j - a) / (b - a);
      }
    k = e;
  }
  const trig = Math.min(o.trig ?? 415, n - 30);
  let iRel = Math.min(n - 1, Math.max(trig, o.iRel ?? trig + 60));
  // ---- 0. release (findRelease: where the in-plane readings settle, searching from the spin-up) and the flight's end.
  // The disc's own release point is kept only if nothing settles (and always in the "old" maths).
  info0.relGiven = iRel; info0.relSrc = "disc";
  if (!old && !o.keepRel) {
    const gzDps = Float64Array.from(gz, v => v - I.bias[2]);
    const k = findRelease(ax, ay, az, gzDps, satG, clipX, clipY, trig, n);
    if (k >= trig) { iRel = k; info0.relSrc = "settled"; }
  }
  const iImp = old ? n : findImpact(ax, ay, az, iRel, n);
  info0.iImp = iImp;
  // ---- 1. the still moment before the throw: "down" and the gyro's zero error (as the disc does)
  const win = Math.floor(0.15 / dt);
  let bias = I.bias.slice(), iStart = 0, q0 = null;
  for (let i = 0; i + win < iRel - win; i++) {
    let still = true; const m = [0, 0, 0, 0, 0, 0];
    for (let k = i; k < i + win; k++) {
      if (Math.hypot(gx[k], gy[k], gz[k]) > 25 || Math.abs(Math.hypot(ax[k], ay[k], az[k]) / GMS - 1) > 0.15) { still = false; break; }
      m[0] += ax[k]; m[1] += ay[k]; m[2] += az[k]; m[3] += gx[k]; m[4] += gy[k]; m[5] += gz[k];
    }
    if (!still) continue;
    q0 = fromUp(m[0], m[1], m[2]);
    const b = [m[3] / win, m[4] / win, m[5] / win];
    if (Math.hypot(b[0] - bias[0], b[1] - bias[1], b[2] - bias[2]) <= 1.5) bias = b;
    iStart = i + win; break;
  }
  if (!q0) {                                               // never still: the quietest 0.1 s before the throw
    const w2 = Math.max(8, Math.floor(0.10 / dt)); let best = 1e9, bi = 0;
    for (let i = 0; i + w2 < iRel - w2; i++) {
      let gm = 0, dm = 0; for (let k = i; k < i + w2; k++) { gm = Math.max(gm, Math.hypot(gx[k], gy[k], gz[k])); dm = Math.max(dm, Math.abs(Math.hypot(ax[k], ay[k], az[k]) / GMS - 1)); }
      const sc = gm / 60 + dm / 0.25; if (sc < best) { best = sc; bi = i; }
    }
    const m = [0, 0, 0]; for (let k = bi; k < bi + w2; k++) { m[0] += ax[k]; m[1] += ay[k]; m[2] += az[k]; }
    q0 = fromUp(m[0], m[1], m[2]); iStart = bi + w2;
  }
  // ---- 2. spin about the disc's axis: the gyro, and where it is maxed a ramp up to the flight's spin
  const wz = new Float64Array(n);
  for (let k = 0; k < n; k++) wz[k] = (gz[k] - bias[2]) * D2R;
  // The flight's spin, between release and the end of the flight: the gyro, if it isn't maxed there. If it is: the
  // wobble's turning rate (turnRate) over kI = (I3 - I1) / I1, and the off-centre sensor's steady force
  // |c| = (w^2 + wp^2 / 2) r with a calibrated radius r (wp: the wobble's own rate) - weighed together when both are
  // there. Last resort: the disc's own number (o.spinRpm), else the gyro's top.
  const kI = I.kI > 0.5 && I.kI < 1.1 ? I.kI : 0.93;
  const f0 = Math.min(n - 1, iRel + 4), f1 = Math.max(f0, Math.min(n, iImp - 3));
  let fSum = 0, fSat = 0; for (let k = f0; k < f1; k++) { fSum += wz[k]; fSat += satG[k]; }
  const fN = f1 - f0, sgn = fSum < 0 ? -1 : 1;
  let wFlight = fN ? fSum / fN : 0, spinSrc = "gyro";
  const spin = { kI };
  if (fN >= 6) {
    const gxs = gx.subarray(f0, f1).map(v => (v - bias[0]) * D2R), gys = gy.subarray(f0, f1).map(v => (v - bias[1]) * D2R);
    let wp2 = 0; for (let i = 0; i < fN; i++) wp2 += gxs[i] ** 2 + gys[i] ** 2;
    const wpMean2 = wp2 / fN;                                // the wobble's rate, squared (with a misaligned axis' share - small)
    const cx = median(ax.subarray(f0, f1)), cy = median(ay.subarray(f0, f1)), cM = Math.hypot(cx, cy);
    spin.c = [cx, cy]; spin.wp = Math.sqrt(wpMean2);
    if (fSat > fN / 4 && !old) {
      const tr = turnRate(gxs, gys, dt);
      // the wobble's: enough of it, a straight line, at least half a turn, the same way round as the gyro says
      const okB = !!tr && tr.mag > 600 * D2R && tr.rms < 0.45 && tr.turns >= 0.5 && Math.sign(tr.w) === sgn;
      const wB = okB ? Math.abs(tr.w) / kI : 0;
      const wA = I.radius > 0.0005 ? Math.sqrt(Math.max(0, cM / I.radius - wpMean2 / 2)) : 0;
      spin.wobble = okB ? wB * 60 / TAU : null; spin.force = wA ? wA * 60 / TAU : null; spin.fit = tr;
      let w = 0;
      if (wA && wB) {                                        // both: weighed (radius ~4 %; wobble ~3 % plus its fit)
        const sA = 0.04, sB = 0.03 + tr.rms / Math.max(1, tr.turns * TAU);
        w = (wA / sA ** 2 + wB / sB ** 2) / (1 / sA ** 2 + 1 / sB ** 2); spinSrc = "wobble+force";
        if (Math.abs(wA - wB) / wB > 0.15) { w = wB; spinSrc = "wobble (force disagrees: radius?)"; }
      } else if (wB) { w = wB; spinSrc = "wobble"; }
      else if (wA) { w = wA; spinSrc = "force"; }
      if (w > Math.abs(wFlight)) wFlight = sgn * w;
      else if (o.spinRpm && o.spinRpm * TAU / 60 > Math.abs(wFlight)) { wFlight = sgn * o.spinRpm * TAU / 60; spinSrc = "disc"; }
      else spinSrc = "gyro's top (at least)";
      if (wB && cM > 0.3 * GMS) spin.radius = cM / (wB * wB + wpMean2 / 2);   // what this throw says the radius is
    } else if (fSat > fN / 4 && o.spinRpm) { wFlight = sgn * o.spinRpm * TAU / 60; spinSrc = "disc"; }
    else if (!fSat && !old && Math.abs(wFlight) > 60 * TAU / 60) {
      // the gyro saw this flight's spin: what it says about this disc, for the throws it won't see. kI from the wobble's
      // turning rate; the radius from the steady force (once it is big enough to read well)
      const tr = turnRate(gxs, gys, dt);
      if (tr && tr.mag > 600 * D2R && tr.rms < 0.3 && tr.turns >= 1 && Math.sign(tr.w) === sgn) spin.kIObs = Math.abs(tr.w / wFlight);
      if (cM > 0.5 * GMS) spin.radiusObs = cM / (wFlight * wFlight + wpMean2 / 2);
    }
  } else if (o.spinRpm) { wFlight = sgn * o.spinRpm * TAU / 60; spinSrc = "disc"; }
  info0.spinSrc = spinSrc; info0.spin = spin; info0.flight = [f0, f1];
  // Where the gyro is maxed: a curve that only rises, from its last reading to the flight's spin at release. Hermite
  // (the last reading's rate of change in, level at release) unless step 4 finds a shape that fits the pull's force
  // (which turns in the disc's axes as the disc spins) clearly better - by 30 % or more; smaller wins are noise.
  const gTop = 32767 * GL * D2R;
  let c0 = -1; for (let k = iStart; k <= iRel; k++) if (satG[k]) { c0 = k; break; }
  const L = iRel - c0 + 1, g0 = c0 > iStart ? wz[c0 - 1] : sgn * gTop, dW = wFlight - g0;
  let m0 = c0 - 3 > iStart ? (wz[c0 - 1] - wz[c0 - 3]) / 2 : dW / L;      // per sample, kept to what a rising curve can have
  if (m0 * dW < 0) m0 = 0; if (Math.abs(m0 * L) > 3 * Math.abs(dW)) m0 = 3 * dW / L;
  const hermite = u => (m0 * L * (u ** 3 - 2 * u * u + u) + dW * (-2 * u ** 3 + 3 * u * u)) / (dW || 1);
  const alz = new Float64Array(n);
  const setRamp = shape => {
    if (c0 >= 0) for (let k = c0; k < n; k++) {
      if (!satG[k] && k > iRel) continue;
      wz[k] = k <= iRel ? g0 + dW * shape((k - c0 + 1) / L) : wFlight;
      if (Math.abs(wz[k]) < gTop && satG[k]) wz[k] = Math.sign(wz[k] || sgn) * gTop;   // at least the gyro's top
    }
    for (let k = 0; k < n; k++) { const a = Math.max(0, k - 2), b = Math.min(n - 1, k + 2); alz[k] = (wz[b] - wz[a]) / ((b - a) * dt); }
  };
  setRamp(hermite);
  // ---- 3. where the sensor sits: off the axis by r, toward minus the flight's steady force; its size from the
  // calibration, else from this throw (the steady force over the spin squared)
  let r = [0, 0, 0];
  if (spin.c && Math.abs(wFlight) > 5) {
    const [cx, cy] = spin.c, m = Math.hypot(cx, cy);
    const rm = I.radius > 0.0005 ? I.radius : spin.radius || m / (wFlight * wFlight + (spin.wp || 0) ** 2 / 2);
    if (m > 1e-3 && rm < 0.03) r = [-cx / m * rm, -cy / m * rm, 0];
  }
  const lever = k => {                                     // the sensor's own spin force: alpha x r + w x (w x r)
    const w = [(gx[k] - bias[0]) * D2R, (gy[k] - bias[1]) * D2R, wz[k]];
    return cross([0, 0, alz[k]], r).map((v, i) => v + cross(w, cross(w, r))[i]);
  };
  // ---- 4. the pull's force through the readings the accelerometer cut off
  const fx = Float64Array.from(ax), fy = Float64Array.from(ay), fz = Float64Array.from(az);
  const info = Object.assign(info0, { clippedA: 0, clippedG: 0, filled: 0 });
  for (let k = iStart; k <= iRel; k++) { if (clipX[k] || clipY[k] || clipZ[k]) info.clippedA++; if (satG[k]) info.clippedG++; }
  if (!old) {
    let a0 = -1;
    for (let k = iStart; k <= Math.min(n - 1, iRel + 3); k++) if (clipX[k] || clipY[k]) { a0 = k; break; }
    const first = a0 < 0 ? c0 : c0 < 0 ? a0 : Math.min(a0, c0);
    if (first >= 0) {
      const w0 = Math.max(iStart, first - 40), w1 = Math.min(n, iRel + 4);
      const ok = Uint8Array.from({ length: n }, (_, k) => dup[k] ? 0 : 1);
      const run = () => {
        const th = [], B = [];
        let t = 0;
        for (let k = w0; k < w1; k++) { if (k > w0) t += 0.5 * (wz[k - 1] + wz[k]) * dt; th.push(t); const L = lever(k); B.push([L[0], L[1]]); }
        const cart = fitPullForce(ax, ay, clipX, clipY, ok, th, B, w0, w1, o.dk || 5, o.smooth ?? 0.5);
        return { th, fit: o.cartesian ? cart : fitPolar(th, B, w0, cart, o.sM ?? 0.2, o.sP ?? 40000) };
      };
      let best = run();
      if (c0 >= 0 && !o.cartesian && !o.noRampSearch) {
        // shapes from "most of the spin-up early" to "most of it late": 1 - (1 - u^a)^b
        const herm = best; let bestShape = null;
        for (const a of [0.6, 1, 1.6, 2.5, 4]) for (const b of [0.6, 1, 1.6, 2.5, 4]) {
          const shape = u => 1 - (1 - u ** a) ** b;
          setRamp(shape); const r = run();
          if (r.fit.cost < best.fit.cost) { best = r; bestShape = shape; }
        }
        if (!bestShape || best.fit.cost > 0.7 * herm.fit.cost) { best = herm; bestShape = hermite; }
        setRamp(bestShape);
        info.ramp = bestShape === hermite ? "smooth" : "fitted";
      }
      const fit = best.fit;
      for (let k = w0; k < w1; k++) {
        if (clipX[k] || dup[k]) { fx[k] = fit.model(k, 0); info.filled++; }
        if (clipY[k] || dup[k]) { fy[k] = fit.model(k, 1); }
      }
      info.fitWindow = [w0, w1]; info.fit = fit; info.th = best.th;
    }
  }
  // ---- 5. add it up: attitude from the gyro, velocity from the force (minus the sensor's spin force), in world axes
  let q = q0.slice(), v = [0, 0, 0], p = [0, 0, 0];
  const path = [], att = [], vel = [];
  for (let k = iStart; k < n; k++) {
    const w = [(gx[k] - bias[0]) * D2R, (gy[k] - bias[1]) * D2R, wz[k]];
    q = qnorm(qmul(q, qexp(w, dt)));
    let f = [fx[k], fy[k], fz[k]];
    if (!old) { const L = lever(k); f = [f[0] - L[0], f[1] - L[1], f[2] - L[2]]; }
    const aw = qrot(q, f);
    v = [v[0] + aw[0] * dt, v[1] + aw[1] * dt, v[2] + (aw[2] - GMS) * dt];
    p = [p[0] + v[0] * dt, p[1] + v[1] * dt, p[2] + v[2] * dt];
    path.push(p.slice()); att.push(q.slice()); vel.push(v.slice());
    if (k === iRel) info.rel = { q: q.slice(), v: v.slice(), p: p.slice() };
  }
  let vr = info.rel.v;
  if (old && r[0] + r[1] !== 0) {                          // the disc's own lever-arm correction, once, at release
    const w = sgn * Math.abs(wFlight), c = qrot(info.rel.q, [-w * r[1], w * r[0], 0]);
    vr = [vr[0] - c[0], vr[1] - c[1], vr[2] - c[2]];
  }
  const six = Object.assign(sixFrom(info.rel.q, vr, sgn > 0), { spin: Math.abs(wFlight) * 60 / TAU, heading: relHeading(q0, vr) });
  return { six, info: Object.assign(info, { iStart, iRel, r, dt }), path, att, vel, q0, iStart, wz, fx, fy, fz };
}

G.DiscTrack = { reconstruct, sixFrom, relHeading, fitPullForce, fitPolar, findRelease, findImpact, turnRate, median };
})(typeof window !== "undefined" ? window : globalThis);
