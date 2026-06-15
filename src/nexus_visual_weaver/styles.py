"""CSS for the command center dashboard."""

APP_CSS = """
:root {
  --nw-bg: #05070a;
  --nw-panel: #090d12;
  --nw-panel-2: #10161d;
  --nw-panel-3: #151c24;
  --nw-line: #222a33;
  --nw-line-strong: #33404c;
  --nw-text: #f3f7fb;
  --nw-muted: #97a4ae;
  --nw-faint: #66737d;
  --nw-red: #ff365f;
  --nw-red-soft: #46121d;
  --nw-cyan: #20d9e8;
  --nw-blue: #6b7dff;
  --nw-violet: #b45cff;
  --nw-green: #26d782;
  --nw-amber: #e8b44e;
}
body, .gradio-container {
  background: var(--nw-bg) !important;
  color: var(--nw-text) !important;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}
.gradio-container { max-width: none !important; padding: 0 !important; }
footer { display: none !important; }
.nw-app {
  min-height: 100vh;
  background:
    linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px),
    linear-gradient(180deg, rgba(255,255,255,.018) 1px, transparent 1px),
    linear-gradient(180deg, #070a0e 0%, #05070a 52%, #06090d 100%),
    var(--nw-bg);
  background-size: 48px 48px, 48px 48px, auto;
}
.nw-topbar {
  min-height: 64px;
  display: grid;
  grid-template-columns: 220px 138px 164px minmax(200px, 1fr) 132px 150px 178px 138px 190px;
  gap: 0;
  align-items: stretch;
  border-bottom: 1px solid #171c22;
  background: rgba(5, 7, 10, 0.98);
  box-shadow: 0 1px 0 rgba(255,255,255,.035), 0 12px 36px rgba(0,0,0,.36);
}
.nw-brand {
  display: flex;
  align-items: center;
  padding: 0 22px;
  font-size: 22px;
  font-weight: 650;
  letter-spacing: 0;
  border-right: 1px solid var(--nw-line);
  color: var(--nw-text);
  white-space: nowrap;
}
.nw-brand span { color: var(--nw-red); margin-right: 10px; font-weight: 850; }
.nw-brand strong { font-size: 18px; font-weight: 650; white-space: nowrap; }
.nw-topbar strong,
.nw-panel strong,
.nw-inspector strong {
  color: var(--nw-text);
}
.nw-topitem, .nw-budget, .nw-status, .nw-adult {
  padding: 10px 18px;
  border-right: 1px solid var(--nw-line);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
  min-width: 0;
}
.nw-topitem small, .nw-budget small, .nw-adult small, .nw-status small { color: var(--nw-muted); font-size: 11px; line-height: 1.2; }
.nw-topitem strong, .nw-budget strong, .nw-status strong, .nw-adult strong { font-size: 13px; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nw-topitem i {
  position: absolute;
  width: 6px;
  height: 6px;
  border-right: 1px solid var(--nw-muted);
  border-bottom: 1px solid var(--nw-muted);
  transform: rotate(45deg);
  right: 18px;
}
.nw-gmr { gap: 5px; }
.nw-space strong { color: var(--nw-cyan); }
.nw-meter { height: 8px; background: #20262d; border-radius: 8px; overflow: hidden; margin-top: 5px; box-shadow: inset 0 0 0 1px rgba(255,255,255,.05); }
.nw-meter i { display: block; height: 100%; background: linear-gradient(90deg, var(--nw-red), #ff6b7f); box-shadow: 0 0 16px rgba(255,54,95,.34); }
.nw-live-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: var(--nw-green); box-shadow: 0 0 12px rgba(38,215,130,.7); margin-right: 7px; vertical-align: -1px; }
.nw-status { position: relative; }
.nw-status .nw-live-dot { position: absolute; top: 21px; left: 18px; }
.nw-status > strong { padding-left: 18px; }
.nw-toggle {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  gap: 7px;
  min-height: 24px;
  padding: 2px 8px 2px 3px;
  border: 1px solid var(--nw-line-strong);
  border-radius: 999px;
  color: var(--nw-muted);
  font-size: 11px;
}
.nw-toggle i { width: 20px; height: 20px; border-radius: 50%; background: #bac2c9; box-shadow: inset 0 -3px 8px rgba(0,0,0,.35); }
.nw-toggle.is-on { color: var(--nw-amber); border-color: rgba(232,180,78,.45); }
.nw-locked {
  display: grid;
  grid-template-columns: 38px 1fr;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-left: 1px solid var(--nw-line);
  color: #ff6b7d;
  background: linear-gradient(90deg, rgba(255,54,95,.12), rgba(255,54,95,.04));
}
.nw-locked b { border: 1px solid rgba(255,54,95,.55); border-radius: 5px; padding: 7px 6px; text-align: center; font-size: 13px; }
.nw-locked span { font-size: 11px; line-height: 1.25; }
.nw-trust-strip {
  display: grid;
  grid-template-columns: minmax(260px, 1.2fr) repeat(4, minmax(160px, 1fr));
  gap: 8px;
  padding: 8px;
  border-bottom: 1px solid #171c22;
  background:
    linear-gradient(90deg, rgba(38,215,130,.08), transparent 38%),
    rgba(5, 7, 10, .98);
}
.nw-trust-primary,
.nw-trust-card {
  min-height: 62px;
  border: 1px solid var(--nw-line);
  border-radius: 7px;
  background:
    linear-gradient(135deg, rgba(255,255,255,.04), transparent 42%),
    rgba(255,255,255,.018);
  padding: 9px 11px;
  display: grid;
  align-content: center;
  gap: 4px;
}
.nw-trust-primary {
  border-color: rgba(38,215,130,.34);
  background:
    linear-gradient(135deg, rgba(38,215,130,.12), transparent 46%),
    rgba(255,255,255,.02);
}
.nw-trust-primary small {
  color: var(--nw-green);
  font-size: 10px;
  font-weight: 800;
}
.nw-trust-primary strong {
  color: var(--nw-text);
  font-size: 14px;
  line-height: 1.2;
}
.nw-trust-primary span,
.nw-trust-card span {
  color: var(--nw-muted);
  font-size: 11px;
  line-height: 1.35;
}
.nw-trust-card .nw-badge {
  margin-bottom: 1px;
}
.nw-icon { width: 18px; height: 18px; stroke: currentColor; fill: none; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.nw-shell {
  display: grid;
  grid-template-columns: 118px minmax(650px, 1fr) 360px;
  grid-template-rows: 570px auto;
  gap: 8px;
  padding: 8px 8px 0;
}
.nw-rail {
  grid-row: 1 / span 2;
  background: linear-gradient(180deg, rgba(11, 15, 20, .98), rgba(6, 9, 12, .98));
  border: 1px solid var(--nw-line);
  border-radius: 7px;
  padding: 8px 6px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.nw-rail-main { display: grid; gap: 6px; }
.nw-rail .nw-icon { width: 21px; height: 21px; }
.nw-rail-foot { margin-top: auto; display: grid; gap: 8px; }
.nw-rail-foot div {
  border: 1px solid var(--nw-line);
  border-radius: 7px;
  background: rgba(255,255,255,.025);
  color: var(--nw-muted);
  padding: 9px 8px;
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: 2px 7px;
}
.nw-rail-foot strong { font-size: 11px; line-height: 1.25; }
.nw-rail-foot span { grid-column: 2; color: var(--nw-muted); font-size: 11px; }
.nw-rail-foot .nw-icon { color: var(--nw-green); grid-row: 1 / span 2; width: 19px; height: 19px; align-self: center; }
.nw-rail-foot div:last-child .nw-icon { color: var(--nw-muted); }
.nw-rail-foot div:last-child { margin-bottom: 70px; }
.nw-rail::after {
  content: "Runs 112   Queue 2";
  color: var(--nw-muted);
  font-size: 11px;
  padding: 11px 6px 3px;
  border-top: 1px solid var(--nw-line);
}
.nw-rail-item {
  background: transparent;
  border: 1px solid transparent;
  color: #c9d0d8;
  border-radius: 7px;
  padding: 13px 10px;
  font-size: 12px;
  display: flex;
  gap: 10px;
  justify-content: flex-start;
  align-items: center;
  width: 100%;
  min-height: 54px;
}
.nw-rail-item span {
  color: currentColor;
  font-size: 12px;
  font-weight: 560;
}
.nw-rail-item.active {
  color: var(--nw-text);
  border-color: rgba(255,54,95,.32);
  background: linear-gradient(90deg, rgba(255,54,95,.20), rgba(255,54,95,.05));
  box-shadow: inset 3px 0 0 var(--nw-red);
}
.nw-panel {
  background: linear-gradient(180deg, rgba(14, 19, 25, .97), rgba(7, 11, 15, .98));
  border: 1px solid var(--nw-line);
  border-radius: 7px;
  box-shadow: 0 18px 55px rgba(0, 0, 0, .28), inset 0 1px 0 rgba(255,255,255,.04);
}
.nw-panel-head {
  min-height: 50px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--nw-line);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.nw-panel-head strong { font-size: 15px; font-weight: 620; }
.nw-panel-head small { display: block; color: var(--nw-muted); font-size: 12px; margin-top: 3px; }
.nw-panel-head button,
.nw-tools button,
.nw-tools select,
.nw-panel-head select,
.nw-beat select {
  min-height: 28px;
  border: 1px solid var(--nw-line-strong);
  background: rgba(255,255,255,.025);
  color: var(--nw-text);
  border-radius: 5px;
  font-size: 11px;
  padding: 4px 9px;
}
.nw-tools { display: flex; align-items: center; gap: 8px; color: var(--nw-muted); font-size: 12px; }
.nw-tools .nw-icon { width: 15px; height: 15px; }
.nw-static-tools span,
.nw-chip,
.nw-mini-chip {
  min-height: 26px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--nw-line-strong);
  background: rgba(255,255,255,.025);
  color: var(--nw-muted);
  border-radius: 5px;
  font-size: 11px;
  padding: 4px 8px;
  white-space: nowrap;
}
.nw-mini-chip { width: fit-content; min-height: 22px; padding: 2px 7px; }
.nw-canvas { overflow: hidden; height: 570px; }
.nw-graph { width: 100%; min-height: 548px; display: block; background: #070b0f; }
.nw-edges path {
  fill: none;
  stroke: var(--nw-cyan);
  stroke-width: 2.2;
  opacity: .82;
}
.nw-node rect {
  fill: rgba(13, 18, 24, .96);
  stroke: var(--nw-line-strong);
  stroke-width: 1.25;
  filter: drop-shadow(0 16px 18px rgba(0,0,0,.25));
}
.nw-node-red rect { stroke: rgba(255,54,95,.74); }
.nw-node-violet rect { stroke: rgba(180,92,255,.72); }
.nw-node-blue rect { stroke: rgba(107,125,255,.72); }
.nw-node-cyan rect { stroke: rgba(32,217,232,.74); }
.nw-node-green rect { stroke: rgba(38,215,130,.68); }
.nw-node-amber rect { stroke: rgba(232,180,78,.78); }
.nw-node-title { fill: var(--nw-text); font-size: 15px; font-weight: 650; }
.nw-node-line { fill: #cbd4dc; font-size: 12px; }
.nw-node-footer { fill: var(--nw-muted); font-size: 11px; }
.nw-node-sep { stroke: rgba(255,255,255,.08); stroke-width: 1; }
.nw-node-ok { fill: var(--nw-green); }
.nw-thumb { stroke: rgba(255,255,255,.16); stroke-width: 1; fill: #17202a; }
.nw-thumb-0 { fill: #101417; }
.nw-thumb-1 { fill: #1e2428; }
.nw-thumb-2 { fill: #33111b; }
.nw-thumb-3 { fill: #0f2630; }
.nw-legend { padding: 0 16px 13px; display: flex; gap: 8px; flex-wrap: wrap; }
.nw-weave-console {
  display: grid;
  grid-template-columns: 1.1fr 1.4fr 1.25fr 1.35fr;
  gap: 8px;
  padding: 0 12px 12px;
}
.nw-console-card {
  min-height: 88px;
  border: 1px solid var(--nw-line);
  border-radius: 6px;
  background:
    linear-gradient(135deg, rgba(255,255,255,.04), transparent 40%),
    rgba(255,255,255,.018);
  padding: 10px;
  display: grid;
  align-content: space-between;
  gap: 5px;
}
.nw-console-primary {
  border-color: rgba(255,54,95,.36);
  background:
    linear-gradient(135deg, rgba(255,54,95,.14), transparent 48%),
    rgba(255,255,255,.02);
}
.nw-console-card small {
  color: var(--nw-faint);
  font-size: 10px;
  font-weight: 760;
  letter-spacing: 0;
}
.nw-console-card strong {
  color: var(--nw-text);
  font-size: 12px;
  line-height: 1.25;
}
.nw-console-card span {
  color: var(--nw-muted);
  font-size: 11px;
  line-height: 1.35;
}
.nw-badge {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 3px 9px;
  border-radius: 5px;
  border: 1px solid var(--nw-line-strong);
  color: var(--nw-muted);
  font-size: 11px;
  font-weight: 650;
  width: fit-content;
}
.nw-pass { color: var(--nw-green); border-color: rgba(46, 229, 157, .35); background: rgba(46, 229, 157, .08); }
.nw-warn { color: var(--nw-amber); border-color: rgba(245, 184, 61, .35); background: rgba(245, 184, 61, .08); }
.nw-accent { color: var(--nw-red); border-color: rgba(244, 63, 94, .35); background: rgba(244, 63, 94, .08); }
.nw-cyan { color: var(--nw-cyan); border-color: rgba(34, 211, 238, .35); background: rgba(34, 211, 238, .08); }
.nw-violet { color: var(--nw-violet); border-color: rgba(180,92,255,.35); background: rgba(180,92,255,.08); }
.nw-blue { color: var(--nw-blue); border-color: rgba(107,125,255,.35); background: rgba(107,125,255,.08); }
.nw-muted { color: var(--nw-muted); }
.nw-inspector { grid-column: 3; grid-row: 1; height: 570px; padding-bottom: 12px; overflow-y: auto; }
.nw-inspector h3 { font-size: 12px; margin: 12px 16px 6px; color: var(--nw-text); font-weight: 620; }
.nw-rings { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; padding: 12px 16px; }
.nw-rings div {
  aspect-ratio: 1;
  border-radius: 999px;
  display: grid;
  place-content: center;
  text-align: center;
  background:
    radial-gradient(circle at center, #10161d 0 55%, transparent 56%),
    conic-gradient(var(--ring) calc(var(--v) * 1%), rgba(255,255,255,.08) 0);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.06);
}
.nw-rings b { font-size: 18px; }
.nw-rings small { color: var(--nw-muted); font-size: 9px; max-width: 58px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.nw-checks, .nw-models, .nw-relay { list-style: none; margin: 0 16px; padding: 0; display: grid; gap: 5px; }
.nw-checks { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.nw-checks li, .nw-models li, .nw-relay li {
  border: 1px solid var(--nw-line);
  border-radius: 5px;
  padding: 6px 8px;
  background: linear-gradient(90deg, rgba(255,255,255,.035), rgba(255,255,255,.016));
  display: flex;
  justify-content: flex-start;
  gap: 8px;
  font-size: 10px;
  color: #dce8ef;
}
.nw-checks li span { color: var(--nw-green); font-weight: 900; }
.nw-models span { color: var(--nw-muted); }
.nw-models li {
  justify-content: space-between;
}
.nw-models strong {
  color: #dce8ef;
  font-size: 11px;
  text-align: right;
}
.nw-relay li {
  display: grid;
  grid-template-columns: minmax(74px, .7fr) minmax(90px, 1fr);
  gap: 4px 8px;
}
.nw-relay span { color: var(--nw-muted); font-size: 11px; }
.nw-relay strong { font-size: 11px; color: #dce8ef; text-align: right; }
.nw-relay em {
  grid-column: 1 / span 2;
  color: var(--nw-muted);
  font-style: normal;
  font-size: 10px;
  line-height: 1.3;
}
.nw-relay-foot { margin: 9px 16px 0; display: flex; flex-wrap: wrap; gap: 6px; }
.nw-scan { margin: 0 16px; padding: 9px; border: 1px solid var(--nw-line); border-radius: 6px; display: grid; gap: 7px; background: rgba(255,255,255,.02); }
.nw-scan > div { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.nw-scan span { color: var(--nw-muted); font-size: 11px; }
.nw-scan i { display: block; height: 7px; border-radius: 7px; background: linear-gradient(90deg, var(--nw-green), rgba(38,215,130,.25)); }
.nw-scan dl { display: grid; grid-template-columns: 90px 1fr; gap: 5px 8px; margin: 0; font-size: 10px; }
.nw-scan dt { color: var(--nw-muted); }
.nw-scan dd { color: #d8e1e8; margin: 0; text-align: right; }
.nw-scan-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 4px;
}
.nw-scan-list li {
  border: 1px solid rgba(255,255,255,.06);
  background: rgba(255,255,255,.022);
  border-radius: 5px;
  padding: 5px 7px;
  color: #d8e1e8;
  font-size: 10px;
  line-height: 1.3;
}
.nw-scan-actions li { color: var(--nw-muted); }
.nw-bottom { grid-column: 2 / span 2; grid-row: 2; display: grid; grid-template-columns: .95fr 1.05fr; gap: 10px; }
.nw-filter-row { display: flex; gap: 7px; padding: 9px 12px 0; overflow-x: auto; }
.nw-filter-row span { border: 1px solid var(--nw-line); border-radius: 5px; padding: 6px 11px; color: var(--nw-muted); font-size: 11px; background: rgba(255,255,255,.018); white-space: nowrap; }
.nw-filter-row span:first-child { color: var(--nw-red); border-color: rgba(255,54,95,.45); }
.nw-swatches, .nw-beats { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(112px, 1fr); gap: 8px; overflow-x: auto; padding: 12px; }
.nw-beats { grid-auto-columns: minmax(128px, 1fr); }
.nw-swatch, .nw-beat { min-height: 134px; border: 1px solid var(--nw-line); border-radius: 6px; padding: 7px; background: rgba(255,255,255,.024); display: grid; align-content: start; gap: 6px; }
.nw-swatch.is-locked {
  border-color: rgba(38,215,130,.34);
  background:
    linear-gradient(135deg, rgba(38,215,130,.08), transparent 42%),
    rgba(255,255,255,.024);
}
.nw-swatch i, .nw-beat i {
  display: block; height: 72px; border-radius: 5px;
  border: 1px solid #303841;
  box-shadow: inset 0 0 24px rgba(0,0,0,.4);
}
.nw-swatch .nw-material-0, .nw-material-0 { background: linear-gradient(135deg, #030405, #20252a 42%, #f5f5f1 44%, #0b0d10 46%, #11181e); }
.nw-swatch .nw-material-1, .nw-material-1 { background: linear-gradient(135deg, #c8c8bd, #545750 35%, #15181b 70%, #08090a); }
.nw-swatch .nw-material-2, .nw-material-2 { background: repeating-linear-gradient(135deg, #080a0d 0 6px, #262a2e 7px 9px, #0d1013 10px 16px); }
.nw-swatch .nw-material-3, .nw-material-3 { background: radial-gradient(circle at 55% 48%, #ff375f 0 7px, #6b1320 8px 19px, #0a0b0d 20px), linear-gradient(135deg, #0b0b0d, #2c0e16); }
.nw-swatch .nw-material-4, .nw-material-4 { background: linear-gradient(160deg, #060709, #111820 45%, #3b4148 46%, #090b0d 70%); }
.nw-swatch .nw-material-5, .nw-material-5 { background: linear-gradient(135deg, #151719, #292d30 40%, #0a0c0f 60%, #1d2226); }
.nw-story-0 { background: linear-gradient(135deg, #29211a, #0c1217 45%, #38444b); }
.nw-story-1 { background: linear-gradient(135deg, #101922, #1a5960 42%, #711c36 70%, #090b0e); }
.nw-story-2 { background: linear-gradient(135deg, #14191e, #363f4a 45%, #0b0d10); }
.nw-story-3 { background: linear-gradient(135deg, #121316, #c9d1d4 50%, #1a1015 55%, #07090c); }
.nw-story-4 { background: linear-gradient(135deg, #0f1115, #2d1a27, #050607 68%); }
.nw-story-5 { background: linear-gradient(135deg, #111820, #333b43 45%, #0a0d11); }
.nw-swatch strong, .nw-beat strong { font-size: 11px; color: var(--nw-text); line-height: 1.25; }
.nw-swatch small, .nw-beat small { font-size: 10px; color: var(--nw-muted); line-height: 1.3; }
.nw-swatch span {
  width: fit-content;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 5px;
  color: var(--nw-faint);
  font-size: 10px;
  padding: 2px 6px;
}
.nw-beat select { min-height: 24px; width: 100%; padding: 2px 5px; color: var(--nw-muted); }
.nw-catalog { padding: 16px; }
.nw-catalog table { width: 100%; border-collapse: collapse; font-size: 12px; }
.nw-catalog th, .nw-catalog td { border-bottom: 1px solid var(--nw-line); padding: 9px 8px; text-align: left; vertical-align: top; }
.nw-catalog th { color: var(--nw-muted); font-size: 11px; text-transform: uppercase; }
#nw-inputs .form, #nw-inputs .block { background: var(--nw-panel) !important; border-color: var(--nw-line) !important; }
#nw-inputs,
#nw-inputs .styler,
#nw-inputs .form,
#nw-inputs .block,
#nw-inputs .wrap,
#nw-inputs .container,
#nw-inputs .upload-container,
#nw-inputs .file-preview,
#nw-inputs .empty,
#nw-inputs .input-container,
#nw-inputs .prose,
#nw-inputs [data-testid],
#nw-inputs fieldset {
  background: #080d12 !important;
  border-color: var(--nw-line) !important;
  color: var(--nw-text) !important;
}
#nw-inputs textarea, #nw-inputs input, #nw-inputs select {
  background: #091018 !important;
  color: var(--nw-text) !important;
  border-color: var(--nw-line-strong) !important;
}
#nw-inputs label, #nw-inputs .label-wrap, #nw-inputs span, #nw-inputs p { color: var(--nw-text) !important; }
#nw-inputs button {
  border-radius: 5px !important;
  border-color: var(--nw-line-strong) !important;
  background: #101820 !important;
  color: var(--nw-text) !important;
  font-size: 13px !important;
}
#nw-inputs button.primary,
#nw-inputs button[variant="primary"] {
  background: linear-gradient(180deg, #ff3b62, #c51a3b) !important;
  border-color: rgba(255,54,95,.58) !important;
}
#nw-operator-actions {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255,255,255,.06);
  gap: 8px !important;
}
#nw-operator-actions button {
  min-height: 34px !important;
  text-transform: uppercase;
  letter-spacing: 0 !important;
  font-size: 11px !important;
  font-weight: 750 !important;
}
#nw-operator-actions button:nth-child(2) {
  border-color: rgba(16,185,129,.42) !important;
}
#nw-operator-actions button:nth-child(3) {
  border-color: rgba(245,158,11,.46) !important;
}
#nw-operator-actions button:nth-child(4) {
  border-color: rgba(148,163,184,.34) !important;
}
.nw-control-panel {
  margin: 8px 8px 10px 8px;
  padding: 12px;
  border: 1px solid var(--nw-line);
  border-radius: 7px;
  background:
    linear-gradient(135deg, rgba(255,54,95,.08), transparent 28%),
    linear-gradient(180deg, rgba(13,18,24,.98), rgba(7,11,15,.98));
  position: sticky;
  top: 0;
  z-index: 20;
  box-shadow: 0 14px 32px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.04);
}
.nw-command-header {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 2px 2px 12px;
  border-bottom: 1px solid rgba(255,255,255,.06);
  margin-bottom: 12px;
}
.nw-command-header small {
  color: var(--nw-red);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0;
}
.nw-command-header strong {
  display: block;
  color: var(--nw-text);
  font-size: 17px;
  font-weight: 680;
  line-height: 1.25;
}
.nw-command-header span {
  display: block;
  color: var(--nw-muted);
  font-size: 12px;
  line-height: 1.35;
  margin-top: 3px;
}
.nw-command-pills {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 7px;
}
#nw-workspace {
  padding: 0 8px;
  gap: 8px !important;
  align-items: stretch;
}
#nw-workspace > .form,
#nw-workspace .block,
#nw-workspace .panel,
#nw-native-rail,
#nw-main-column,
#nw-side-column {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}
#nw-native-rail,
#nw-main-column,
#nw-side-column {
  gap: 8px !important;
}
#nw-section-nav,
#nw-section-nav .form,
#nw-section-nav fieldset,
#nw-section-nav .wrap {
  background: linear-gradient(180deg, rgba(11, 15, 20, .98), rgba(6, 9, 12, .98)) !important;
  border-color: var(--nw-line) !important;
  color: var(--nw-text) !important;
  border-radius: 7px !important;
}
#nw-section-nav label,
#nw-section-nav span {
  color: var(--nw-text) !important;
}
#nw-section-nav .wrap {
  display: grid !important;
  gap: 5px !important;
}
#nw-section-nav input[type="radio"] {
  accent-color: var(--nw-red);
}
.nw-native-rail {
  border: 1px solid var(--nw-line);
  background: linear-gradient(180deg, rgba(12,17,23,.97), rgba(7,10,14,.98));
  border-radius: 7px;
  padding: 12px;
  display: grid;
  gap: 8px;
}
.nw-native-rail strong {
  color: var(--nw-text);
  font-size: 13px;
}
.nw-native-rail span {
  color: var(--nw-muted);
  font-size: 11px;
  line-height: 1.4;
}
#nw-workspace .nw-canvas,
#nw-workspace .nw-inspector {
  grid-column: auto;
  grid-row: auto;
}
#nw-workspace .nw-canvas {
  height: auto;
  min-height: 570px;
}
#nw-workspace .nw-inspector {
  height: auto;
  min-height: 570px;
}
.nw-main-stack,
.nw-side-stack {
  display: grid;
  gap: 8px;
}
.nw-artifacts {
  overflow: hidden;
}
.nw-preview-stage {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) 190px;
  gap: 10px;
  padding: 12px 12px 0;
}
.nw-preview-frame {
  min-height: 190px;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 7px;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(180px, .86fr) 1fr;
  background:
    radial-gradient(circle at 18% 18%, rgba(255,54,95,.18), transparent 32%),
    linear-gradient(135deg, #0a0d11, #111820 52%, #080a0d);
}
.nw-preview-image {
  min-height: 190px;
  display: block;
  background:
    linear-gradient(130deg, rgba(255,255,255,.16) 0 2px, transparent 3px 52%),
    radial-gradient(circle at 42% 34%, #f5f0e8 0 4px, transparent 5px),
    radial-gradient(circle at 44% 50%, #242930 0 30px, transparent 31px),
    linear-gradient(155deg, #050608, #171d23 44%, #4f1020 45%, #07090c 63%);
  border-right: 1px solid rgba(255,255,255,.08);
}
.nw-preview-real-image {
  width: 100%;
  min-height: 190px;
  height: 100%;
  object-fit: cover;
  display: block;
  border-right: 1px solid rgba(255,255,255,.08);
  background: #050608;
}
.nw-preview-caption {
  display: grid;
  align-content: end;
  gap: 6px;
  padding: 16px;
}
.nw-preview-caption small,
.nw-preview-meta small,
.nw-artifact-card small {
  color: var(--nw-faint);
  font-size: 10px;
  font-weight: 760;
  letter-spacing: 0;
}
.nw-preview-caption strong {
  font-size: 15px;
  color: var(--nw-text);
  line-height: 1.25;
}
.nw-preview-caption span {
  color: #cbd5dc;
  font-size: 12px;
  line-height: 1.45;
}
.nw-preview-meta {
  display: grid;
  gap: 8px;
}
.nw-preview-meta div {
  border: 1px solid var(--nw-line);
  border-radius: 6px;
  background: rgba(255,255,255,.024);
  padding: 10px;
  display: grid;
  align-content: center;
  gap: 4px;
}
.nw-preview-meta strong {
  color: var(--nw-text);
  font-size: 12px;
  line-height: 1.25;
}
.nw-preview-ribbon {
  margin: 10px 12px 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.nw-preview-ribbon span {
  min-height: 34px;
  border: 1px solid var(--nw-line);
  border-radius: 6px;
  background: rgba(255,255,255,.02);
  color: #cfd8df;
  font-size: 11px;
  line-height: 1.3;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 9px;
  min-width: 0;
}
.nw-preview-ribbon .nw-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
  color: var(--nw-cyan);
}
.nw-operations {
  overflow: hidden;
}
.nw-operation-grid {
  padding: 12px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.nw-operation-card {
  min-height: 116px;
  border: 1px solid var(--nw-line);
  border-radius: 6px;
  background:
    linear-gradient(135deg, rgba(32,217,232,.07), transparent 34%),
    rgba(255,255,255,.022);
  padding: 11px;
  display: grid;
  align-content: space-between;
  gap: 10px;
}
.nw-operation-card small {
  color: var(--nw-cyan);
  font-size: 10px;
  font-weight: 760;
  letter-spacing: 0;
}
.nw-operation-card strong {
  color: #dce8ef;
  font-size: 12px;
  line-height: 1.4;
  font-weight: 560;
}
.nw-operation-card i {
  display: block;
  height: 5px;
  border-radius: 6px;
  background:
    linear-gradient(90deg, var(--nw-cyan), rgba(32,217,232,.18) 68%, rgba(255,255,255,.06));
  box-shadow: 0 0 14px rgba(32,217,232,.14);
}
.nw-artifact-grid {
  padding: 12px;
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 8px;
}
.nw-artifact-card,
.nw-provider-card {
  border: 1px solid var(--nw-line);
  border-radius: 6px;
  background: linear-gradient(180deg, rgba(255,255,255,.035), rgba(255,255,255,.014));
  padding: 8px;
  display: grid;
  gap: 6px;
  min-width: 0;
}
.nw-artifact-card > small {
  justify-self: end;
}
.nw-artifact-card i {
  display: block;
  height: 86px;
  border-radius: 5px;
  border: 1px solid #303841;
  box-shadow: inset 0 0 24px rgba(0,0,0,.42);
}
.nw-artifact-card strong,
.nw-provider-card strong {
  color: var(--nw-text);
  font-size: 12px;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.nw-artifact-card span,
.nw-provider-card span,
.nw-provider-card small {
  color: var(--nw-muted);
  font-size: 11px;
  line-height: 1.3;
}
.nw-providers {
  overflow: hidden;
}
.nw-provider-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding: 12px;
}
.nw-provider-card {
  min-height: 112px;
}
.nw-provider-meter {
  height: 6px;
  border-radius: 8px;
  background:
    linear-gradient(90deg, var(--nw-green) 0 calc(var(--health) * 1%), #252d35 calc(var(--health) * 1%) 100%);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.05);
}
.nw-provider-card div {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.nw-statusbar {
  height: 54px;
  margin: 8px;
  display: grid !important;
  grid-template-columns: 110px 120px 160px 200px 140px 150px 1fr 160px;
  align-items: stretch;
  border: 1px solid var(--nw-line);
  border-radius: 7px;
  overflow: hidden;
  background: rgba(7, 10, 14, .98);
}
.nw-metric, .nw-autosave {
  border-right: 1px solid var(--nw-line);
  padding: 8px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.nw-metric small, .nw-autosave small { color: var(--nw-muted); font-size: 11px; }
.nw-metric strong, .nw-autosave strong { color: var(--nw-text); font-size: 13px; font-weight: 560; }
.nw-metric-bar::after {
  content: "";
  height: 6px;
  flex: 1;
  border-radius: 8px;
  background: linear-gradient(90deg, var(--nw-green) 0 46%, #232a31 47% 100%);
}
.nw-autosave { justify-content: flex-end; }
.nw-stop {
  margin: 8px;
  border: 1px solid rgba(255,54,95,.55);
  background: linear-gradient(180deg, #f32d56, #bd1739);
  color: white;
  border-radius: 6px;
  font-weight: 650;
  font-size: 13px;
}
.nw-stop-idle {
  display: grid;
  place-items: center;
  border-color: var(--nw-line-strong);
  background: rgba(255,255,255,.025);
  color: var(--nw-muted);
}
.nw-stop-active {
  display: grid;
  place-items: center;
}
@media (max-width: 1100px) {
  .nw-topbar { grid-template-columns: 1fr; }
  .nw-trust-strip { grid-template-columns: 1fr; }
  .nw-shell { grid-template-columns: 1fr; grid-template-rows: auto; }
  .nw-rail, .nw-inspector, .nw-bottom { grid-column: 1; grid-row: auto; }
  .nw-rail { flex-direction: row; overflow-x: auto; }
  .nw-rail-main { display: flex; }
  .nw-rail-foot, .nw-rail::after { display: none; }
  .nw-bottom { grid-template-columns: 1fr; }
  #nw-workspace { flex-direction: column; }
  .nw-command-header, .nw-preview-stage, .nw-preview-frame { grid-template-columns: 1fr; }
  .nw-command-pills { justify-content: flex-start; }
  .nw-operation-grid { grid-template-columns: 1fr; }
  .nw-weave-console, .nw-preview-ribbon { grid-template-columns: 1fr; }
  .nw-artifact-grid, .nw-provider-grid { grid-template-columns: 1fr 1fr; }
  .nw-graph { min-height: 430px; }
  .nw-statusbar { grid-template-columns: 1fr 1fr; height: auto; }
}
@media (max-width: 720px) {
  .nw-artifact-grid, .nw-provider-grid { grid-template-columns: 1fr; }
  .nw-rings { grid-template-columns: repeat(2, 1fr); }
  .nw-checks { grid-template-columns: 1fr; }
}
"""
