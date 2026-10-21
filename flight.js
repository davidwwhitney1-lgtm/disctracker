// ====================================================================
// DiscTracker flight model - shared by the phone app (index.html) and the
// computer simulator (sim.html). Built from scratch; TechDisc's model is closed.
// ====================================================================
// Physics, per 4 ms step:
//   * lift and drag from the angle of attack between the disc plane and
//     the air (relative to wind), as in published frisbee flight models
//   * a pitching moment that depends on airspeed vs the disc's rated speed:
//     nose-down at high speed (TURN rating) and nose-up at low speed (FADE)
//   * gyroscopic precession: the spin turns that pitching moment into a slow
//     roll of the disc (dn/dt = spin_sign * torque / (I * omega)), which is
//     what bends the flight - turn early, fade late
//   * wobble: the disc axis circles its mean direction twice per spin, so the
//     angle of attack swings +-wobble around its mean. Lift and pitching moment
//     are close to linear in angle of attack and average out; drag grows with
//     angle^2, so its average rises by cdAlpha * wobble^2 / 2. The wobble then
//     dies away (aerodynamic damping) with time constant wobbleTauS.
// Flight numbers set the coefficients (speed -> drag and rated airspeed,
// glide -> lift, turn/fade -> pitching moment). Absolute distance is
// approximate; flight SHAPE is the goal. TUNE holds every knob in one place.
const TUNE = {
  // tuned 2026-10-07 against typical amateur flights (driver 60 mph ~320-350 ft with
  // an S-curve, putter, midrange, under/overstable shapes). Re-tune with real landings.
  mass: 0.175, radius: 0.1055, rho: 1.225, inertiaK: 0.6,
  ratedBase: 8, ratedPerSpeed: 1.4,           // rated airspeed m/s = base + per * speed
  cd0Base: 0.095, cd0PerSpeed: 0.003, cdAlpha: 0.8, alpha0Deg: -2,
  cl0Base: 0.06, cl0PerGlide: 0.01, clAlpha: 2.2,
  cmAlpha: 0, kTurn: 0.003, kFade: 0.02, switchAt: 0.5, switchWidth: 0.08,
  spinDecayS: 12,
  // Wobble damping time constant. ESTIMATE from an instrumented Frisbee (Weizman,
  // Tan & Fuss 2020: wobble settled about 1 s after release). Calibrate with real throws.
  wobbleTauS: 0.5,
};

const v3 = {
  add: (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]],
  sub: (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]],
  mul: (a, k) => [a[0] * k, a[1] * k, a[2] * k],
  dot: (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2],
  cross: (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]],
  len: a => Math.hypot(a[0], a[1], a[2]),
  norm: a => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; },
};

// Axes: x = down the throw line, y = LEFT, z = up. Units SI inside, feet out.
// p = { speedMph, spinRpm, hyzer, nose, launch, wobble (deg, axis-cone angle), ccw,
//       disc: {speed, glide, turn, fade}, windMph, windFrom (0 head, 90 right, 180 tail), heightFt }
// Each path point: t (s), x/y/z (ft), nx/ny/nz (disc normal), w (wobble now, deg).
function simulateFlight(p) {
  const T = TUNE, D2R = Math.PI / 180, MPH = 0.44704, FT = 3.28084;
  const A = Math.PI * T.radius ** 2, d = 2 * T.radius, I = T.inertiaK * T.mass * T.radius ** 2;
  const S = p.disc.speed, G = p.disc.glide, TU = p.disc.turn, FA = p.disc.fade;
  const vRated = T.ratedBase + T.ratedPerSpeed * S;
  const CD0 = T.cd0Base - T.cd0PerSpeed * S;
  const CL0 = T.cl0Base + T.cl0PerGlide * G;
  const s = p.ccw ? 1 : -1;                       // +1 counter-clockwise from above
  const W0 = Math.max(0, Math.min(45, p.wobble || 0)) * D2R;

  const L = p.launch * D2R;
  const f = [Math.cos(L), 0, Math.sin(L)];
  let pos = [0, 0, (p.heightFt ?? 4) / FT];
  let vel = v3.mul(f, p.speedMph * MPH);
  // disc normal: perpendicular to the flight, tipped back by NOSE, then rolled
  // toward the fade side by HYZER (fade side: left for clockwise, right for ccw)
  const nPerp = [-Math.sin(L), 0, Math.cos(L)];
  const nNose = v3.norm(v3.sub(v3.mul(nPerp, Math.cos(p.nose * D2R)), v3.mul(f, Math.sin(p.nose * D2R))));
  const left = v3.norm(v3.cross(nNose, f));
  const fadeSide = s < 0 ? left : v3.mul(left, -1);
  let n = v3.norm(v3.add(v3.mul(nNose, Math.cos(p.hyzer * D2R)), v3.mul(fadeSide, Math.sin(p.hyzer * D2R))));
  let omega = Math.max(p.spinRpm, 50) * 2 * Math.PI / 60;

  const w = (p.windMph || 0) * MPH, th = (p.windFrom || 0) * D2R;
  const windVel = v3.mul([Math.cos(th), -Math.sin(th), 0], -w);

  const dt = 0.004, path = [];
  let t = 0, maxH = pos[2], nextRec = 0, wobDragLoss = 0;
  const rec = wob => path.push({ t, x: pos[0] * FT, y: pos[1] * FT, z: Math.max(0, pos[2] * FT), nx: n[0], ny: n[1], nz: n[2], w: wob / D2R });
  while (t < 15) {
    const va = v3.sub(vel, windVel), V = v3.len(va);
    if (V < 0.1) break;
    const vh = v3.mul(va, 1 / V);
    const alpha = -Math.asin(Math.max(-1, Math.min(1, v3.dot(vh, n))));
    const wob = W0 * Math.exp(-t / T.wobbleTauS);
    const q = 0.5 * T.rho * V * V;
    const CL = CL0 + T.clAlpha * alpha;
    const CDw = T.cdAlpha * 0.5 * wob * wob;      // extra drag from the wobble swing
    const CD = CD0 + T.cdAlpha * (alpha - T.alpha0Deg * D2R) ** 2 + CDw;
    let liftDir = v3.sub(n, v3.mul(vh, v3.dot(n, vh)));
    liftDir = v3.len(liftDir) > 1e-6 ? v3.norm(liftDir) : [0, 0, 1];
    const force = v3.add(v3.mul(v3.sub(v3.mul(liftDir, CL), v3.mul(vh, CD)), q * A), [0, 0, -9.81 * T.mass]);
    wobDragLoss += CDw * q * A * V * dt;          // energy the wobble cost (J)
    if (t >= nextRec) { rec(wob); nextRec += 0.02; }
    vel = v3.add(vel, v3.mul(force, dt / T.mass));
    pos = v3.add(pos, v3.mul(vel, dt));

    const hi = 1 / (1 + Math.exp(-((V / vRated) - T.switchAt) / T.switchWidth));   // 1 = fast
    const CM = T.cmAlpha * alpha + T.kTurn * TU * hi + T.kFade * FA * (1 - hi);
    const axis = v3.cross(vh, n);                    // nose-up torque points to the right of the airflow
    if (v3.len(axis) > 1e-6) {
      const tau = v3.mul(v3.norm(axis), q * A * d * CM);
      let dn = v3.mul(tau, s / (I * omega));
      dn = v3.sub(dn, v3.mul(n, v3.dot(dn, n)));
      n = v3.norm(v3.add(n, v3.mul(dn, dt)));
    }
    omega *= 1 - dt / T.spinDecayS;

    t += dt;
    if (pos[2] > maxH) maxH = pos[2];
    if (pos[2] <= 0) break;
  }
  rec(W0 * Math.exp(-t / T.wobbleTauS));
  return { path, distFt: Math.hypot(pos[0], pos[1]) * FT, lateralFt: pos[1] * FT, maxHFt: maxH * FT, timeS: t,
           wobbleEnergyJ: wobDragLoss };
}

// Older firmware (before 2026-10) reported wobble as the angle between the
// rotation vector and the disc axis. For a flat disc that is ~2x the axis-cone
// angle used now: tan(cone) = tan(old) / 2. Approximate (it also included any
// tilt of the board in its mount).
function wobbleFromRateAngle(deg) {
  return Math.atan(Math.tan(Math.min(89, Math.max(0, deg)) * Math.PI / 180) / 2) * 180 / Math.PI;
}

// TechDisc's public simulator (techdisc.com/simulate) reads a throw from its link:
//   v = speed (m/s), spin = rad/s (negative = clockwise from above, e.g. RH backhand),
//   uphill_degrees = launch, hyzer_degrees, nose_up_degrees, wind_speed, wind_angle,
//   speed / glide / turn / weight (kg) = the simulated disc. It has no wobble input.
function techdiscSimUrl(t, disc) {
  const d = disc || { speed: 12, glide: 5, turn: -1 };
  const q = new URLSearchParams({
    v: (t.speed * 0.44704).toFixed(2),
    spin: ((t.ccw ? 1 : -1) * t.spin * 2 * Math.PI / 60).toFixed(2),
    uphill_degrees: (+t.launch).toFixed(1),
    hyzer_degrees: (+t.hyzer).toFixed(1),
    nose_up_degrees: (+t.nose).toFixed(1),
    speed: d.speed, glide: d.glide, turn: d.turn, weight: ((d.weightG || 175) / 1000).toFixed(3),
  });
  return "https://techdisc.com/simulate?" + q.toString();
}

window.DiscFlight = { TUNE, v3, simulateFlight, wobbleFromRateAngle, techdiscSimUrl };
