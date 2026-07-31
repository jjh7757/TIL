/* Maze Relay -- 지하 미로 탈출 + 비동기 릴레이
 *
 * 이 게임의 핵심은 미로가 아니라 출구 앞의 선택이다. 플레이어가 만나는
 * "쓰러진 사람"은 NPC가 아니라 직전에 이 게임을 플레이한 실제 사람이고,
 * 플레이어 자신도 결국 그 자리에 갇혀 다음 사람의 선택을 기다리게 된다.
 *
 * ⚠️ 반전은 outcome 화면까지 절대 노출하지 않는다. 타이틀/조우 화면의 문구를
 *    고칠 때 "이전 플레이어"라는 말이 새어나가지 않게 주의할 것.
 */
(function(){
  "use strict";

  // ---------- Config ----------
  const TILE       = 16;    // source px per tile in the sprite sheets
  const CELL_PX    = 32;    // rendered px per maze cell (2x -- pixel art stays crisp)
  const MAZE_ROWS  = 15;
  const MAZE_COLS  = 25;    // measured: 최단경로 ~97칸, 통로 ~207칸, 막다른 길 ~12개
  const BASE_SPEED = 160;   // px/sec == 5 cells/sec
  const PLAYER_R   = 9;     // collision radius; corridor is 32px so there's slack
  const FOG_INNER_CELLS = 3.4;
  const FOG_OUTER_CELLS = 6.2;

  const MAX_HP        = 3;
  const TRAP_DENSITY  = 0.07;  // share of floor cells that get spikes
  const TRAP_STEP_MS  = 400;   // per animation frame -> 1.6s cycle
  const INVULN_MS     = 1200;
  const KNOCKBACK     = 34;

  const NICK_MAX = 12;
  const PLEA_MAX = 80;

  // ---------- Shared store (Supabase REST) ----------
  // The anon key is public by design (it ships in the page). Never put the
  // service_role key here. Blank these out and the game falls back to
  // localStorage-only, which still plays fine -- just not as a relay.
  const SUPABASE_URL = "https://ykvlsdrholswxrkkuubo.supabase.co";
  const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlrdmxzZHJob2xzd3hya2t1dWJvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODUyMTE1ODUsImV4cCI6MjEwMDc4NzU4NX0.pgnXFS_L6abHsxn0rd5AlJuHUxI5VXgd27MoGGBIZhI";
  const MESSAGES_TABLE = "messages";
  const VERDICTS_TABLE = "message_boosts"; // reused: now stores kill/spare verdicts

  const LS_PLEAS    = "mazeRelay_pleas_v2";
  const LS_VERDICTS = "mazeRelay_verdicts_v2";
  const LS_CLAIMED  = "mazeRelay_claimed_v2";
  const LS_NICK     = "mazeRelay_nick_v2";
  const LS_CHAR     = "mazeRelay_char_v2";

  // Shown when the shared pool has nothing left to hand out. The player is
  // never told which kind they got -- but the outcome screen is honest about
  // it rather than inventing a fake author.
  const SEED_PLEAS = [
    "제발… 살려주세요. 아직 죽고 싶지 않아요.",
    "여기서 이렇게 끝나고 싶지 않아. 부탁이야.",
    "누구든 좋으니, 그냥 지나가 주기만 해도 돼요.",
    "다리를 못 써요. 당신마저 가버리면 정말 끝이에요.",
    "살려주면… 은혜는 꼭 갚을게요. 약속해요.",
    "무서워요. 혼자 있고 싶지 않아요."
  ];

  // Row order must match tools/build_atlases.py. The source pack ships 2-3
  // weapon/idle-timing/recolor variants per body (priest1/2/3) -- those are
  // the SAME character, not different ones, so only one variant per body
  // made it into the atlas. knight/shieldmaiden/dwarf/plucky_girl/witch each
  // come from their own separate reference sheet (see build_atlases.py).
  const CHARACTERS = [
    "priest","skull","vampire","knight",
    "shieldmaiden","dwarf","plucky_girl","witch"
  ];
  // Indices that read as a person rather than a monster -- used as the
  // fallback NPC look before a real claim (with its own char_index) lands.
  const HUMANOID_CHAR_INDICES = [0, 3, 4, 5, 6, 7]; // priest, knight, shieldmaiden, dwarf, plucky_girl, witch

  // ---------- Tile coordinates in tileset.png, as [col,row] ----------
  const T_FLOOR = [
    [1,1],[2,1],[3,1],[4,1],
    [1,2],[2,2],[3,2],[4,2],
    [1,3],[2,3],[3,3],[4,3]
  ];
  const T_WALL_FACE = [2,5]; // wall cell with floor directly below -> brick face
  const T_WALL_TOP  = [2,0]; // everything else -> plain wall body

  // props atlas rows
  const P_PEAKS = 0, P_TORCH = 1, P_SIDE_TORCH = 2, P_FLAG = 3;
  // peaks_*.png ships as extended -> mid -> hidden -> emerging, so play it in
  // this order to get hidden -> emerging -> extended -> mid (a fair telegraph).
  const PEAK_SEQ = [2,3,0,1];
  const PEAK_DANGER_STEP = 2; // index into PEAK_SEQ that is fully extended

  // ---------- Utility ----------
  function clamp(v,min,max){ return Math.max(min, Math.min(max, v)); }
  function lerp(a,b,t){ return a+(b-a)*t; }
  function escapeHtml(s){
    return String(s).replace(/[&<>"']/g,c=>({
      "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"
    }[c]));
  }
  // Placeholder for profanity/spam filtering. Deliberately a no-op for now --
  // see CLAUDE.md: moderation was consciously deferred, and Moirai (the closest
  // predecessor to this game) was permanently shut down over exactly this.
  function sanitize(text){
    return String(text||"").trim().slice(0, PLEA_MAX);
  }
  // Nicknames are player-supplied, so any particle glued to one has to be
  // picked at runtime: 받침 있으면 "이", 없으면 "가".
  function josa(word, withBatchim, without){
    const s = String(word||"");
    if(!s) return without;
    const code = s.charCodeAt(s.length-1);
    const isHangul = code >= 0xAC00 && code <= 0xD7A3;
    // non-Hangul tails (latin, digits) fall back to the no-받침 form
    const batchim = isHangul && (code - 0xAC00) % 28 !== 0;
    return batchim ? withBatchim : without;
  }
  function hash2(a,b){
    let h = (a*73856093) ^ (b*19349663);
    h = (h ^ (h>>>13)) >>> 0;
    return h;
  }

  function mulberry32(seed){
    return function(){
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // ---------- Maze generation ----------
  // Randomized DFS (recursive backtracker) -> a perfect maze: exactly one route
  // between any two cells, so the player meets junctions with no visible right
  // answer and eats the backtrack when a branch dead-ends. Do NOT "simplify"
  // this into randomly walling off open cells -- that erodes down to a single
  // unavoidable corridor, which is EASIER because there is nothing to get wrong.
  function generateMaze(seed){
    const rows = MAZE_ROWS, cols = MAZE_COLS;
    const grid = Array.from({length:rows},()=>new Array(cols).fill(false));
    const rand = mulberry32(seed);
    const DIRS = [[-2,0],[2,0],[0,-2],[0,2]];

    grid[0][0] = true;
    const stack = [[0,0]];
    while(stack.length){
      const [cr,cc] = stack[stack.length-1];
      const dirs = DIRS.slice();
      for(let i=dirs.length-1;i>0;i--){
        const j = Math.floor(rand()*(i+1));
        const t = dirs[i]; dirs[i]=dirs[j]; dirs[j]=t;
      }
      let advanced = false;
      for(const [dr,dc] of dirs){
        const nr=cr+dr, nc=cc+dc;
        if(nr<0||nr>=rows||nc<0||nc>=cols) continue;
        if(grid[nr][nc]) continue;
        grid[cr+dr/2][cc+dc/2] = true;  // knock out the wall between rooms
        grid[nr][nc] = true;
        stack.push([nr,nc]);
        advanced = true;
        break;
      }
      if(!advanced) stack.pop();
    }

    function firstOpenInCol(col){
      for(let r=0;r<rows;r++) if(grid[r][col]) return [r,col];
      return null;
    }
    const start = firstOpenInCol(0);
    const exit  = firstOpenInCol(cols-1);

    return { grid, rows, cols, start, exit, traps: placeTraps(grid,rows,cols,start,exit,rand) };
  }

  // Spikes go on open cells away from the start and off the exit tile. Each one
  // gets its own phase so the field doesn't pulse in unison (that would let the
  // player time every trap in the maze off a single observation).
  function placeTraps(grid,rows,cols,start,exit,rand){
    const traps = [];
    for(let r=0;r<rows;r++){
      for(let c=0;c<cols;c++){
        if(!grid[r][c]) continue;
        if(Math.abs(r-start[0])+Math.abs(c-start[1]) < 4) continue; // safe spawn
        if(r===exit[0] && c===exit[1]) continue;
        if(Math.abs(r-exit[0])+Math.abs(c-exit[1]) < 2) continue;   // keep the meeting clear
        if(rand() < TRAP_DENSITY){
          traps.push({ r, c, phase: Math.floor(rand()*PEAK_SEQ.length) });
        }
      }
    }
    return traps;
  }

  // ---------- Supabase / storage ----------
  function remoteConfigured(){ return SUPABASE_URL !== "" && SUPABASE_ANON_KEY !== ""; }
  function sbHeaders(extra){
    return Object.assign({
      apikey: SUPABASE_ANON_KEY,
      Authorization: `Bearer ${SUPABASE_ANON_KEY}`
    }, extra||{});
  }
  function lsGet(key){
    try{
      const raw = localStorage.getItem(key);
      const arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr : [];
    }catch(e){ return []; }
  }
  function lsPush(key,obj){
    const arr = lsGet(key);
    arr.push(obj);
    try{ localStorage.setItem(key, JSON.stringify(arr)); }catch(e){}
  }

  /* Claim exactly one plea, consumed atomically so no two players can ever be
     handed the same one. The heavy lifting is a Postgres function using
     FOR UPDATE SKIP LOCKED (see SETUP.md); PostgREST exposes it at /rpc/.
     Returns {id,text,author,seed:false} or a seed fallback. */
  async function claimPlea(nickname){
    // Only fall back to this browser's own local echo when the remote pool
    // was genuinely unreachable (no backend configured, or the request
    // itself failed) -- NOT when it was reachable and just came back empty.
    // Otherwise clearing the shared table doesn't give an honest "you're
    // first" run: this same browser's old test pleas keep resurfacing
    // because they're still sitting in localStorage from before the clear.
    let remoteFailed = !remoteConfigured();
    if(remoteConfigured()){
      try{
        const res = await fetch(`${SUPABASE_URL}/rest/v1/rpc/claim_message`, {
          method:"POST",
          headers: sbHeaders({ "Content-Type":"application/json" }),
          body: JSON.stringify({ p_nickname: nickname })
        });
        if(!res.ok) throw new Error(`rpc ${res.status}`);
        const rows = await res.json();
        const row = Array.isArray(rows) ? rows[0] : rows;
        if(row && row.text){
          return {
            id: row.id, text: row.text, author: row.author || null,
            charIndex: Number.isInteger(row.char_index) ? row.char_index : null,
            seed: false
          };
        }
        // Reached Supabase fine, it just had nothing to hand back -- the
        // shared pool is genuinely empty, so skip straight to the seed line.
      }catch(e){
        console.warn("[maze-relay] 공유 메시지를 가져오지 못했습니다.", e);
        remoteFailed = true;
      }
    }
    if(remoteFailed){
      // local-only fallback: consume from this browser's own unclaimed pleas
      const claimed = lsGet(LS_CLAIMED).map(x=>x.id);
      const mine = lsGet(LS_PLEAS).filter(p=>claimed.indexOf(p.id)<0 && p.author!==nickname);
      if(mine.length){
        const pick = mine[0];
        lsPush(LS_CLAIMED, { id: pick.id, by: nickname, ts: Date.now() });
        return {
          id: pick.id, text: pick.text, author: pick.author||null,
          charIndex: Number.isInteger(pick.charIndex) ? pick.charIndex : null,
          seed: false
        };
      }
    }
    const t = SEED_PLEAS[Math.floor(Math.random()*SEED_PLEAS.length)];
    return { id:null, text:t, author:null, charIndex:null, seed:true };
  }

  async function savePleaRemote(text, author, charIndex){
    const id = `l${Date.now()}_${Math.floor(Math.random()*1e6)}`;
    lsPush(LS_PLEAS, { id, text, author, charIndex, ts: Date.now() });
    if(!remoteConfigured()) return;
    const res = await fetch(`${SUPABASE_URL}/rest/v1/${MESSAGES_TABLE}`, {
      method:"POST",
      headers: sbHeaders({ "Content-Type":"application/json", Prefer:"return=minimal" }),
      body: JSON.stringify({ text, author, char_index: charIndex })
    });
    if(!res.ok) throw new Error(`insert ${res.status}`);
  }

  // Fire-and-forget: logging the verdict must never stall the story beat.
  function recordVerdict(claim, verdict, judge){
    if(!claim) return;
    lsPush(LS_VERDICTS, {
      message_id: claim.id, message_text: claim.text,
      judge, verdict, ts: Date.now()
    });
    if(!remoteConfigured() || claim.seed) return;
    fetch(`${SUPABASE_URL}/rest/v1/${VERDICTS_TABLE}`, {
      method:"POST",
      headers: sbHeaders({ "Content-Type":"application/json", Prefer:"return=minimal" }),
      body: JSON.stringify({
        message_id: claim.id, message_text: claim.text, judge, verdict
      })
    }).catch(e=>console.warn("[maze-relay] 판정 기록 실패", e));
  }

  /* What happened to the pleas this player left in earlier runs.
     Returns [{text, judge, verdict}] -- verdict null while nobody has met them yet. */
  async function fetchMyFate(nickname){
    if(remoteConfigured()){
      try{
        const mRes = await fetch(
          `${SUPABASE_URL}/rest/v1/${MESSAGES_TABLE}`
          + `?select=id,text,claimed_by&author=eq.${encodeURIComponent(nickname)}`
          + `&order=created_at.desc&limit=20`,
          { headers: sbHeaders() });
        if(!mRes.ok) throw new Error(`fetch ${mRes.status}`);
        const mine = await mRes.json();
        if(!mine.length) return [];
        const ids = mine.map(m=>m.id).join(",");
        const vRes = await fetch(
          `${SUPABASE_URL}/rest/v1/${VERDICTS_TABLE}`
          + `?select=message_id,judge,verdict&message_id=in.(${ids})`,
          { headers: sbHeaders() });
        const verdicts = vRes.ok ? await vRes.json() : [];
        const byId = new Map(verdicts.map(v=>[v.message_id, v]));
        return mine.map(m=>{
          const v = byId.get(m.id);
          return { text:m.text, judge: v?v.judge:(m.claimed_by||null), verdict: v?v.verdict:null };
        });
      }catch(e){
        console.warn("[maze-relay] 이전 기록을 불러오지 못했습니다.", e);
      }
    }
    const verdicts = lsGet(LS_VERDICTS);
    return lsGet(LS_PLEAS).filter(p=>p.author===nickname).reverse().map(p=>{
      const v = verdicts.find(x=>x.message_id===p.id);
      return { text:p.text, judge: v?v.judge:null, verdict: v?v.verdict:null };
    });
  }

  // ---------- Sound (Web Audio synth + two real samples) ----------
  // The AudioContext is created lazily on the first real click -- browsers block
  // audio before a user gesture, and a synthetic .click() does NOT count, so
  // this can only ever be verified by an actual pointer event. Background music
  // and the hurt sample are routed through this same context (via a GainNode
  // each) so everything shares one lazy-init point and the music can be ducked
  // from plain code without touching the DOM.
  const MUSIC_VOLUME = 0.32;
  const HURT_SAMPLE_VOLUME = 0.55;

  const SoundFX = (function(){
    let ctx = null;
    let bootstrapped = false;
    let hurtBuffer = null;   // filled in async once bootstrap() fetches it
    let hurtBufferFailed = false;

    function ac(){
      if(!ctx) ctx = new (window.AudioContext||window.webkitAudioContext)();
      if(ctx.state === "suspended") ctx.resume();
      return ctx;
    }
    function tone(freq,start,dur,type,peak){
      const c=ac(), osc=c.createOscillator(), g=c.createGain();
      osc.type=type; osc.frequency.setValueAtTime(freq,start);
      g.gain.setValueAtTime(0,start);
      g.gain.linearRampToValueAtTime(peak,start+0.02);
      g.gain.exponentialRampToValueAtTime(0.0001,start+dur);
      osc.connect(g).connect(c.destination);
      osc.start(start); osc.stop(start+dur+0.05);
    }
    function sweep(f0,f1,start,dur,type,peak){
      const c=ac(), osc=c.createOscillator(), g=c.createGain();
      osc.type=type; osc.frequency.setValueAtTime(f0,start);
      osc.frequency.exponentialRampToValueAtTime(f1,start+dur);
      g.gain.setValueAtTime(0,start);
      g.gain.linearRampToValueAtTime(peak,start+0.02);
      g.gain.exponentialRampToValueAtTime(0.0001,start+dur);
      osc.connect(g).connect(c.destination);
      osc.start(start); osc.stop(start+dur+0.05);
    }
    function noise(start,dur,peak){
      const c=ac(), n=Math.max(1,Math.floor(c.sampleRate*dur));
      const buf=c.createBuffer(1,n,c.sampleRate), d=buf.getChannelData(0);
      for(let i=0;i<n;i++) d[i]=(Math.random()*2-1)*(1-i/n);
      const src=c.createBufferSource(); src.buffer=buf;
      const g=c.createGain(); g.gain.setValueAtTime(peak,start);
      src.connect(g).connect(c.destination); src.start(start);
    }

    // Fire-and-forget: a slow network shouldn't delay anything, and if it never
    // resolves the game still plays -- hurt() falls back to the synthesized cue.
    function loadHurtSample(){
      fetch("assets/sounds/hurt.wav")
        .then(r=>r.arrayBuffer())
        .then(buf=>ac().decodeAudioData(buf))
        .then(decoded=>{ hurtBuffer = decoded; })
        .catch(e=>{ hurtBufferFailed = true; console.warn("[maze-relay] hurt.wav 로드 실패", e); });
    }
    function playHurtSample(){
      if(!hurtBuffer) return false;
      const c = ac(), src = c.createBufferSource(), g = c.createGain();
      src.buffer = hurtBuffer; g.gain.value = HURT_SAMPLE_VOLUME;
      src.connect(g).connect(c.destination);
      src.start();
      return true;
    }

    function startMusic(){
      // Plain <audio> playback, deliberately NOT routed through the
      // AudioContext graph (no createMediaElementSource) -- Chrome outputs
      // silence for a MediaElementAudioSourceNode whose media it can't
      // verify as same-origin, and a file:// page's own file:// audio
      // doesn't count as verified. Volume goes through el.volume instead of
      // a GainNode, which works everywhere this way.
      try{
        const el = new Audio("assets/music/theme.mp3");
        el.loop = true;
        el.volume = MUSIC_VOLUME;
        el.play().catch(e=>console.warn("[maze-relay] 배경음악 재생 실패(자동재생 정책일 수 있음)", e));
      }catch(e){ console.warn("[maze-relay] 배경음악 초기화 실패", e); }
    }

    return {
      // Called once, from the very first real button click alongside the
      // AudioContext's own lazy creation -- starting music any earlier would
      // hit the same autoplay block the AudioContext itself is dodging.
      bootstrap(){
        if(bootstrapped) return;
        bootstrapped = true;
        startMusic();
        loadHurtSample();
      },
      click(){ tone(880, ac().currentTime, 0.05, "square", 0.04); },
      hurt(){
        if(playHurtSample()) return;
        // sample still loading (or failed) -- don't let a hit go silent
        const t=ac().currentTime; sweep(440,110,t,0.22,"sawtooth",0.2); noise(t,0.12,0.09);
      },
      spike(){ const t=ac().currentTime; noise(t,0.06,0.05); tone(1400,t,0.04,"square",0.03); },
      death(){ const t=ac().currentTime; sweep(300,60,t,1.1,"sawtooth",0.2); noise(t,0.4,0.1); },
      encounter(){ const t=ac().currentTime; tone(196,t,1.2,"sine",0.1); tone(233,t+0.25,1.2,"sine",0.07); },
      kill(){ const t=ac().currentTime; noise(t,0.18,0.16); sweep(220,70,t+0.02,0.5,"sawtooth",0.18); },
      spare(){ const t=ac().currentTime; [392,523.25,659.25].forEach((f,i)=>tone(f,t+i*0.1,0.5,"triangle",0.1)); },
      betray(){ const t=ac().currentTime; noise(t,0.1,0.18); sweep(880,90,t+0.05,0.7,"square",0.16); },
      reveal(){ const t=ac().currentTime; [261.63,329.63,392,523.25].forEach((f,i)=>tone(f,t+i*0.14,1.0,"sine",0.09)); }
    };
  })();
  document.addEventListener("click",(e)=>{
    if(!(e.target && e.target.tagName === "BUTTON")) return;
    SoundFX.click();
    SoundFX.bootstrap();
  });

  // ---------- Assets ----------
  const IMG = {};
  function loadImages(){
    const list = {
      tiles: "assets/tileset.png",
      chars: "assets/atlas_chars.png",
      props: "assets/atlas_props.png"
    };
    return Promise.all(Object.keys(list).map(k=>new Promise(resolve=>{
      const im = new Image();
      im.onload = ()=>{ IMG[k]=im; resolve(); };
      im.onerror = ()=>{ console.warn("[maze-relay] 이미지 로드 실패:", list[k]); resolve(); };
      im.src = list[k];
    })));
  }

  // ---------- DOM ----------
  const canvas = document.getElementById("gameCanvas");
  const ctx = canvas.getContext("2d");
  const hud = document.getElementById("hud");
  const heartsEl = document.getElementById("hearts");
  const statusText = document.getElementById("statusText");
  const $ = id=>document.getElementById(id);

  // ---------- Game state ----------
  let state = "title"; // title|setup|playing|encounter|aftermath|plea|outcome
  let maze = null;
  let player = { x:0, y:0, hp:MAX_HP, invulnUntil:0, facing:1 };
  let keys = { w:false,a:false,s:false,d:false };
  let camera = { x:0, y:0 };
  let lastFrame = 0, animClock = 0;

  let nickname = "";
  let charIndex = 0;
  let npcCharIndex = 0;
  let currentClaim = null;   // the plea handed to us this run
  let myChoice = null;       // "killed" | "spared"
  let diedToTrap = false;

  function fitCanvas(){
    // clamp low as well as high: a hidden/zero-sized window would otherwise
    // give a 0x0 canvas and the whole game would render to nothing
    const w = clamp(window.innerWidth  || 960, 320, 1100);
    const h = clamp(window.innerHeight || 600, 240, 700);
    canvas.width = Math.floor(w);
    canvas.height = Math.floor(h);
  }
  window.addEventListener("resize", fitCanvas);

  function worldPx(){ return { w: maze.cols*CELL_PX, h: maze.rows*CELL_PX }; }
  function cellCenter(rc){ return { x: rc[1]*CELL_PX+CELL_PX/2, y: rc[0]*CELL_PX+CELL_PX/2 }; }
  function isWall(r,c){
    if(r<0||r>=maze.rows||c<0||c>=maze.cols) return true;
    return !maze.grid[r][c];
  }
  function collides(x,y,rad){
    const minC=Math.floor((x-rad)/CELL_PX), maxC=Math.floor((x+rad)/CELL_PX);
    const minR=Math.floor((y-rad)/CELL_PX), maxR=Math.floor((y+rad)/CELL_PX);
    for(let r=minR;r<=maxR;r++) for(let c=minC;c<=maxC;c++) if(isWall(r,c)) return true;
    return false;
  }
  function hideAllOverlays(){
    document.querySelectorAll(".overlay.show").forEach(el=>el.classList.remove("show"));
  }
  function show(id){ $(id).classList.add("show"); }

  function renderHearts(){
    heartsEl.innerHTML = "";
    for(let i=0;i<MAX_HP;i++){
      const d = document.createElement("div");
      d.className = "heart" + (i < player.hp ? "" : " lost");
      heartsEl.appendChild(d);
    }
  }

  // ---------- Drawing helpers ----------
  function drawTile(coord, dx, dy){
    if(!IMG.tiles) return;
    ctx.drawImage(IMG.tiles, coord[0]*TILE, coord[1]*TILE, TILE, TILE, dx, dy, CELL_PX, CELL_PX);
  }
  function drawChar(index, frame, cx, cy, size){
    if(!IMG.chars) return;
    const s = size || CELL_PX;
    ctx.drawImage(IMG.chars, frame*TILE, index*TILE, TILE, TILE,
      Math.round(cx-s/2), Math.round(cy-s/2), s, s);
  }
  function drawProp(row, frame, dx, dy){
    if(!IMG.props) return;
    ctx.drawImage(IMG.props, frame*TILE, row*TILE, TILE, TILE, dx, dy, CELL_PX, CELL_PX);
  }

  // ---------- Flow ----------
  function goTitle(){
    hideAllOverlays();
    hud.style.display = "none";
    state = "title";
    show("titleScreen");
  }

  function goSetup(){
    hideAllOverlays();
    state = "setup";
    nickname = localStorage.getItem(LS_NICK) || "";
    // clamp: a returning player may have a stored index from when the picker
    // had more entries, which would sample past the end of the atlas
    charIndex = clamp(parseInt(localStorage.getItem(LS_CHAR)||"0",10) || 0,
                      0, CHARACTERS.length-1);
    $("nicknameInput").value = nickname;
    $("nickCount").textContent = nickname.length;
    buildCharGrid();
    validateSetup();
    show("setupScreen");
  }

  function buildCharGrid(){
    const grid = $("charGrid");
    grid.innerHTML = "";
    CHARACTERS.forEach((name,i)=>{
      const cell = document.createElement("button");
      cell.className = "char-cell" + (i===charIndex ? " selected" : "");
      cell.type = "button";
      cell.title = name;
      const cv = document.createElement("canvas");
      cv.width = TILE; cv.height = TILE;
      cell.appendChild(cv);
      cell.addEventListener("click", ()=>{
        charIndex = i;
        grid.querySelectorAll(".char-cell").forEach(el=>el.classList.remove("selected"));
        cell.classList.add("selected");
      });
      grid.appendChild(cell);
    });
  }

  // The picker tiles animate off the main loop so every option idles in sync
  // with what the player will actually control.
  function paintCharGrid(){
    if(state !== "setup" || !IMG.chars) return;
    const frame = Math.floor(animClock/180) % 4;
    const cells = $("charGrid").querySelectorAll(".char-cell canvas");
    cells.forEach((cv,i)=>{
      const c = cv.getContext("2d");
      c.clearRect(0,0,TILE,TILE);
      c.drawImage(IMG.chars, frame*TILE, i*TILE, TILE, TILE, 0, 0, TILE, TILE);
    });
  }

  function validateSetup(){
    const v = $("nicknameInput").value.trim();
    $("enterMazeBtn").disabled = v.length === 0;
  }

  function startRun(){
    hideAllOverlays();
    nickname = $("nicknameInput").value.trim().slice(0,NICK_MAX) || nickname;
    try{
      localStorage.setItem(LS_NICK, nickname);
      localStorage.setItem(LS_CHAR, String(charIndex));
    }catch(e){}

    maze = generateMaze((Date.now() ^ 0x5f3a) | 0);
    const sc = cellCenter(maze.start);
    player.x = sc.x; player.y = sc.y;
    player.hp = MAX_HP;
    player.invulnUntil = 0;
    currentClaim = null;
    myChoice = null;
    diedToTrap = false;
    // Until the claim lands, fall back to a humanoid so the figure at the end
    // always reads as a person rather than a monster.
    npcCharIndex = HUMANOID_CHAR_INDICES[hash2(maze.exit[0], maze.exit[1]) % HUMANOID_CHAR_INDICES.length];

    state = "playing";
    hud.style.display = "flex";
    renderHearts();
    statusText.textContent = "출구를 찾는 중…";

    // Claim the plea now, while the player still has a maze to walk, so the
    // encounter never stalls on a network round trip. The figure at the exit is
    // drawn as whatever character that player actually picked -- so the reveal
    // is pointing at something the player already saw.
    claimPlea(nickname).then(c=>{
      currentClaim = c;
      if(c && Number.isInteger(c.charIndex) && c.charIndex >= 0 && c.charIndex < CHARACTERS.length){
        npcCharIndex = c.charIndex;
      }
    });
  }

  function hitSpike(){
    const now = performance.now();
    if(now < player.invulnUntil) return;
    player.hp -= 1;
    player.invulnUntil = now + INVULN_MS;
    renderHearts();
    SoundFX.hurt();
    if(player.hp <= 0){ triggerTrapDeath(); return; }
    // shove the player back toward the cell they came from
    const cr = Math.floor(player.y/CELL_PX), cc = Math.floor(player.x/CELL_PX);
    const cen = cellCenter([cr,cc]);
    let bx = player.x - cen.x, by = player.y - cen.y;
    const len = Math.hypot(bx,by) || 1;
    bx = bx/len*KNOCKBACK; by = by/len*KNOCKBACK;
    if(!collides(player.x+bx, player.y, PLAYER_R)) player.x += bx;
    if(!collides(player.x, player.y+by, PLAYER_R)) player.y += by;
    statusText.textContent = "다쳤다…";
  }

  function triggerTrapDeath(){
    diedToTrap = true;
    state = "aftermath";
    hud.style.display = "none";
    SoundFX.death();
    $("aftermathTitle").textContent = "쓰러졌다";
    $("aftermathText").innerHTML =
      "가시밭을 넘지 못했다. 몸이 말을 듣지 않는다.<br><br>" +
      "출구는 결국 보지 못했다. 이제 이 자리에서 누군가를 기다리는 수밖에 없다.";
    $("toPleaBtn").textContent = "…";
    show("aftermathScreen");
  }

  function triggerEncounter(){
    state = "encounter";
    hud.style.display = "none";
    SoundFX.encounter();
    const claim = currentClaim
      || { text: SEED_PLEAS[0], author:null, charIndex:null, seed:true, id:null };
    currentClaim = claim;
    $("encounterSpeech").innerHTML =
      escapeHtml(claim.text) + `<span class="who">— 출구 앞에 쓰러진 사람</span>`;
    show("encounterScreen");
  }

  function chooseKill(){
    myChoice = "killed";
    SoundFX.kill();
    recordVerdict(currentClaim, "killed", nickname);
    hideAllOverlays();
    state = "aftermath";
    $("aftermathTitle").textContent = "출구는 없었다";
    $("aftermathText").innerHTML =
      "그는 더 이상 움직이지 않는다.<br><br>" +
      "그를 넘어 출구로 향한다. 그런데 그 자리엔 벽뿐이다. 출구라고 믿었던 건 " +
      "그저 미로의 끝, 막다른 길이었다.<br><br>" +
      "돌아가려는 순간 다리에 힘이 풀린다. 여기까지가 끝이다.";
    $("toPleaBtn").textContent = "…";
    show("aftermathScreen");
  }

  function chooseSpare(){
    myChoice = "spared";
    SoundFX.spare();
    recordVerdict(currentClaim, "spared", nickname);
    hideAllOverlays();
    state = "aftermath";
    $("aftermathTitle").textContent = "고맙다는 말";
    $("aftermathText").innerHTML =
      "그는 몇 번이고 고맙다고 했다. 부축해 일으켜 세우자 다리에 힘이 들어가는 게 느껴졌다.<br><br>" +
      "그리고 등 뒤에서 둔탁한 소리가 났다.<br><br>" +
      "바닥이 가까워진다. 멀어지는 발소리를 들으며, 그가 왜 그렇게까지 " +
      "간절했는지 이제야 알 것 같다. 여기서 나갈 수 있는 건 한 사람뿐이었다.";
    setTimeout(()=>SoundFX.betray(), 500);
    $("toPleaBtn").textContent = "…";
    show("aftermathScreen");
  }

  function goPlea(){
    hideAllOverlays();
    state = "plea";
    $("pleaInput").value = "";
    $("pleaCount").textContent = "0";
    $("pleaStatus").textContent = "";
    $("savePleaBtn").disabled = false;
    $("pleaPrompt").innerHTML =
      "움직일 수 없다. 언젠가 누군가 이 앞을 지나갈 것이다.<br>그 사람에게 뭐라고 애원하겠습니까?";
    show("pleaScreen");
  }

  async function submitPlea(){
    const text = sanitize($("pleaInput").value);
    if(!text){ skipPlea(); return; }
    const btn = $("savePleaBtn");
    btn.disabled = true;
    $("pleaStatus").textContent = "남기는 중…";
    try{
      await savePleaRemote(text, nickname, charIndex);
      $("pleaStatus").textContent = "";
    }catch(e){
      console.warn("[maze-relay] 메시지 공유 실패", e);
      $("pleaStatus").textContent = "공유에 실패해 이 기기에만 저장했어요.";
      await new Promise(r=>setTimeout(r,900));
    }
    showOutcome(true);
  }
  function skipPlea(){ showOutcome(false); }

  /* The reveal. Everything up to here has been played straight as dungeon
     fiction; this is the only screen that tells the player the person at the
     exit was real -- and it must stay honest when they happened to draw a seed
     message instead (never invent an author). */
  async function showOutcome(leftPlea){
    hideAllOverlays();
    state = "outcome";
    SoundFX.reveal();

    const panelTitle = document.querySelector("#outcomeScreen h2");
    const body = $("outcomeBody");
    const met = !diedToTrap && currentClaim;
    const real = met && !currentClaim.seed;

    panelTitle.textContent = real ? "그 사람은 NPC가 아니었습니다"
                                  : "이 미로에 대하여";

    let html = "";

    if(real){
      const who = currentClaim.author
        ? `<strong>${escapeHtml(currentClaim.author)}</strong>`
        : "<strong>이름을 남기지 않은 누군가</strong>";
      const verdictLabel = myChoice === "killed"
        ? `<span class="verdict-killed">죽였습니다</span>`
        : `<span class="verdict-spared">살려줬습니다</span>`;
      html += `<div class="reveal">
        출구 앞에서 당신에게 말을 건 사람은 ${who}입니다.
        당신보다 먼저 이 미로에 들어왔던 실제 플레이어이고,
        그 말은 대사가 아니라 그 사람이 직접 입력한 문장입니다.<br><br>
        그도 당신과 똑같이 출구 앞에서 누군가를 만났고, 똑같이 여기에 갇혔습니다.<br><br>
        당신은 그를 ${verdictLabel}.
      </div>`;
    } else if(met){
      html += `<div class="reveal">
        이 미로에서 만나는 사람은 원래 <strong>직전에 플레이한 실제 사람</strong>입니다.
        그 대사는 프로그램이 쓴 게 아니라 그 사람이 직접 남긴 문장이고요.<br><br>
        다만 이번엔 아직 아무도 남긴 말이 없어서, 당신이 만난 건 미리 준비된 문장이었습니다.
        당신이 첫 번째입니다.
      </div>`;
    } else {
      html += `<div class="reveal">
        이 미로의 출구 앞에는 <strong>직전에 플레이한 실제 사람</strong>이 쓰러져 있습니다.
        당신은 거기까지 가지 못했습니다.
      </div>`;
    }

    if(leftPlea){
      html += `<p class="body-text">그리고 방금 당신이 남긴 말은, 다음에 이 미로에
        들어오는 사람이 출구 앞에서 듣게 됩니다. 그 사람도 당신을 죽일지 살릴지 고르게 됩니다.</p>`;
    } else {
      html += `<p class="body-text">당신은 아무 말도 남기지 않았습니다.
        다음 사람은 당신 대신 다른 누군가를 만나게 됩니다.</p>`;
    }

    html += `<div id="fateBlock" class="hint">이전 기록을 확인하는 중…</div>`;
    body.innerHTML = html;
    show("outcomeScreen");

    // previous runs' pleas and what became of them
    const fates = await fetchMyFate(nickname);
    const judged = fates.filter(f=>f.verdict);
    const fateEl = $("fateBlock");
    if(!fateEl) return;
    if(!judged.length){
      fateEl.className = "hint";
      fateEl.innerHTML = "아직 당신이 남긴 말을 들은 사람은 없습니다. 나중에 다시 들어와서 확인해 보세요.";
      return;
    }
    fateEl.className = "reveal";
    fateEl.innerHTML = "<strong>당신이 전에 남긴 말</strong><br><br>" + judged.map(f=>{
      const v = f.verdict === "killed"
        ? `<span class="verdict-killed">죽였습니다</span>`
        : `<span class="verdict-spared">살려줬습니다</span>`;
      const who = f.judge ? escapeHtml(f.judge) : "누군가";
      const g = f.judge ? josa(f.judge, "이", "가") : "가";
      return `“${escapeHtml(f.text)}”<br>→ <strong>${who}</strong>${g} 그 말을 들었고, 당신을 ${v}.`;
    }).join("<br><br>");
  }

  // ---------- Input ----------
  window.addEventListener("keydown",(e)=>{
    const k = e.key.toLowerCase();
    if(k in keys && state === "playing"){ keys[k]=true; e.preventDefault(); }
  });
  window.addEventListener("keyup",(e)=>{
    const k = e.key.toLowerCase();
    if(k in keys) keys[k]=false;
  });
  window.addEventListener("blur",()=>{ keys.w=keys.a=keys.s=keys.d=false; });

  $("toSetupBtn").addEventListener("click", goSetup);
  $("nicknameInput").addEventListener("input",(e)=>{
    $("nickCount").textContent = e.target.value.length;
    validateSetup();
  });
  $("enterMazeBtn").addEventListener("click", startRun);
  $("killBtn").addEventListener("click", chooseKill);
  $("spareBtn").addEventListener("click", chooseSpare);
  $("toPleaBtn").addEventListener("click", goPlea);
  $("pleaInput").addEventListener("input",(e)=>{
    $("pleaCount").textContent = e.target.value.length;
  });
  $("savePleaBtn").addEventListener("click", submitPlea);
  $("skipPleaBtn").addEventListener("click", skipPlea);
  $("retryBtn").addEventListener("click", startRun);
  $("toTitleBtn").addEventListener("click", goTitle);

  // ---------- Update ----------
  function update(dt){
    animClock += dt*1000;
    if(state !== "playing") return;

    let dx=0, dy=0;
    if(keys.w) dy-=1;
    if(keys.s) dy+=1;
    if(keys.a) dx-=1;
    if(keys.d) dx+=1;
    if(dx && dy){ dx*=0.7071; dy*=0.7071; }
    if(dx) player.facing = dx>0 ? 1 : -1;

    const nx = player.x + dx*BASE_SPEED*dt;
    const ny = player.y + dy*BASE_SPEED*dt;
    if(!collides(nx, player.y, PLAYER_R)) player.x = nx;
    if(!collides(player.x, ny, PLAYER_R)) player.y = ny;

    // spike contact -- only while fully extended
    const pr = Math.floor(player.y/CELL_PX), pc = Math.floor(player.x/CELL_PX);
    for(const t of maze.traps){
      if(t.r!==pr || t.c!==pc) continue;
      const step = (Math.floor(animClock/TRAP_STEP_MS) + t.phase) % PEAK_SEQ.length;
      if(step === PEAK_DANGER_STEP) hitSpike();
      break;
    }

    // Camera is dead-centred on the player with no clamping to the world box.
    // Clamping would pin the view in a corner (the maze is barely larger than a
    // typical viewport) and the fog hides the out-of-bounds void anyway.
    camera.x = player.x;
    camera.y = player.y;

    // reached the far end
    const ex = cellCenter(maze.exit);
    if(Math.hypot(player.x-ex.x, player.y-ex.y) < CELL_PX*0.7) triggerEncounter();
  }

  // ---------- Render ----------
  function render(){
    ctx.fillStyle = "#140f18";
    ctx.fillRect(0,0,canvas.width,canvas.height);
    paintCharGrid();
    if(!maze || state==="title" || state==="setup") return;

    ctx.save();
    ctx.translate(Math.round(canvas.width/2 - camera.x), Math.round(canvas.height/2 - camera.y));

    // only draw what's on screen -- the maze is bigger than the viewport
    const c0 = Math.max(0, Math.floor((camera.x-canvas.width/2)/CELL_PX)-1);
    const c1 = Math.min(maze.cols-1, Math.ceil((camera.x+canvas.width/2)/CELL_PX)+1);
    const r0 = Math.max(0, Math.floor((camera.y-canvas.height/2)/CELL_PX)-1);
    const r1 = Math.min(maze.rows-1, Math.ceil((camera.y+canvas.height/2)/CELL_PX)+1);

    for(let r=r0;r<=r1;r++){
      for(let c=c0;c<=c1;c++){
        const dx = c*CELL_PX, dy = r*CELL_PX;
        if(maze.grid[r][c]){
          drawTile(T_FLOOR[hash2(r,c) % T_FLOOR.length], dx, dy);
          // Floor and brick sit at almost the same value in this tileset, which
          // makes corridors hard to trace. Sink the floor and drop a contact
          // shadow under any wall above it so walls read as raised blocks.
          ctx.fillStyle = "rgba(0,0,0,0.26)";
          ctx.fillRect(dx, dy, CELL_PX, CELL_PX);
          if(r>0 && !maze.grid[r-1][c]){
            ctx.fillStyle = "rgba(0,0,0,0.34)";
            ctx.fillRect(dx, dy, CELL_PX, 4);
            ctx.fillStyle = "rgba(0,0,0,0.16)";
            ctx.fillRect(dx, dy+4, CELL_PX, 4);
          }
        } else {
          // a wall with open floor below shows its brick face; the rest is body
          const openBelow = r+1 < maze.rows && maze.grid[r+1][c];
          drawTile(openBelow ? T_WALL_FACE : T_WALL_TOP, dx, dy);
          // sparse wall torches double as landmarks in the fog
          if(openBelow && hash2(r,c) % 11 === 0){
            drawProp(P_SIDE_TORCH, Math.floor(animClock/140)%4, dx, dy);
          }
        }
      }
    }

    // traps
    for(const t of maze.traps){
      if(t.r<r0||t.r>r1||t.c<c0||t.c>c1) continue;
      const step = (Math.floor(animClock/TRAP_STEP_MS) + t.phase) % PEAK_SEQ.length;
      drawProp(P_PEAKS, PEAK_SEQ[step], t.c*CELL_PX, t.r*CELL_PX);
    }

    // the figure at the end -- visible as soon as the fog reaches them
    const ex = cellCenter(maze.exit);
    if(state === "playing" || state === "encounter"){
      ctx.save();
      ctx.globalAlpha = 0.9;
      drawChar(npcCharIndex, Math.floor(animClock/220)%4, ex.x, ex.y+3, CELL_PX*0.9);
      ctx.restore();
    }

    // player (blink while invulnerable)
    const blinking = performance.now() < player.invulnUntil
      && Math.floor(animClock/90)%2 === 0;
    if(!blinking){
      ctx.save();
      if(player.facing < 0){
        ctx.translate(player.x*2, 0);
        ctx.scale(-1,1);
        drawChar(charIndex, Math.floor(animClock/180)%4, player.x, player.y, CELL_PX*0.95);
      } else {
        drawChar(charIndex, Math.floor(animClock/180)%4, player.x, player.y, CELL_PX*0.95);
      }
      ctx.restore();
    }

    ctx.restore();

    // fog of war
    if(state === "playing" || state === "encounter"){
      const sx = canvas.width/2  + (player.x - camera.x);
      const sy = canvas.height/2 + (player.y - camera.y);
      const g = ctx.createRadialGradient(sx,sy,CELL_PX*FOG_INNER_CELLS, sx,sy,CELL_PX*FOG_OUTER_CELLS);
      g.addColorStop(0,"rgba(20,15,24,0)");
      g.addColorStop(1,"rgba(20,15,24,1)");
      ctx.fillStyle = g;
      ctx.fillRect(0,0,canvas.width,canvas.height);
    }
  }

  function loop(ts){
    if(!lastFrame) lastFrame = ts;
    const dt = Math.min(0.05,(ts-lastFrame)/1000);
    lastFrame = ts;
    update(dt);
    render();
    requestAnimationFrame(loop);
  }

  fitCanvas();
  loadImages().then(()=>{ requestAnimationFrame(loop); });
})();
