// === BASE PATH ===
const BASE = document.querySelector('base')?.getAttribute('href')?.replace(/\/$/, '')
  || window.location.pathname.replace(/\/$/, '');

// === TEAM DATA ===
const TEAM_NAMES = {
  ATL: "Hawks", BOS: "Celtics", BKN: "Nets", CHA: "Hornets",
  CHI: "Bulls", CLE: "Cavaliers", DAL: "Mavericks", DEN: "Nuggets",
  DET: "Pistons", GSW: "Warriors", HOU: "Rockets", IND: "Pacers",
  LAC: "Clippers", LAL: "Lakers", MEM: "Grizzlies", MIA: "Heat",
  MIL: "Bucks", MIN: "Timberwolves", NOP: "Pelicans", NYK: "Knicks",
  OKC: "Thunder", ORL: "Magic", PHI: "76ers", PHX: "Suns",
  POR: "Trail Blazers", SAC: "Kings", SAS: "Spurs", TOR: "Raptors",
  UTA: "Jazz", WAS: "Wizards",
};

const TEAM_IDS = {
  ATL: 1610612737, BOS: 1610612738, BKN: 1610612751, CHA: 1610612766,
  CHI: 1610612741, CLE: 1610612739, DAL: 1610612742, DEN: 1610612743,
  DET: 1610612765, GSW: 1610612744, HOU: 1610612745, IND: 1610612754,
  LAC: 1610612746, LAL: 1610612747, MEM: 1610612763, MIA: 1610612748,
  MIL: 1610612749, MIN: 1610612750, NOP: 1610612740, NYK: 1610612752,
  OKC: 1610612760, ORL: 1610612753, PHI: 1610612755, PHX: 1610612756,
  POR: 1610612757, SAC: 1610612758, SAS: 1610612759, TOR: 1610612761,
  UTA: 1610612762, WAS: 1610612764,
};

function teamName(tri) { return TEAM_NAMES[tri] || tri; }
function teamLogo(tri) {
  const id = TEAM_IDS[tri];
  return id ? `https://cdn.nba.com/logos/nba/${id}/primary/L/logo.svg` : "";
}

// Mapping nom complet -> tricode pour les classements
const TEAM_NAME_TO_TRI = {};
for (const [tri, name] of Object.entries(TEAM_NAMES)) {
  TEAM_NAME_TO_TRI[name.toLowerCase()] = tri;
}

function teamLogoByName(fullName) {
  // Essaie d'abord le tricode direct
  if (TEAM_IDS[fullName]) return teamLogo(fullName);
  // Sinon cherche par le nom de l'equipe dans le nom complet
  for (const [name, tri] of Object.entries(TEAM_NAME_TO_TRI)) {
    if (fullName.toLowerCase().includes(name.toLowerCase())) return teamLogo(tri);
  }
  return "";
}

// === DOM ELEMENTS ===
const gamesListEl = document.getElementById("games-list");
const noGamesEl = document.getElementById("no-games");
const gamesDateEl = document.getElementById("games-date");
const eastStandingsEl = document.getElementById("east-standings");
const westStandingsEl = document.getElementById("west-standings");
const datePicker = document.getElementById("date-picker");
const refreshBtn = document.getElementById("refresh-btn");
const spinnerEl = document.getElementById("spinner");
const errorEl = document.getElementById("error-message");

// === TABS ===
const tabs = document.querySelectorAll(".tab");
const tabContents = document.querySelectorAll(".tab-content");

tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    tabs.forEach(t => t.classList.remove("active"));
    tabContents.forEach(tc => tc.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(tab.dataset.tab + "-section").classList.add("active");
    if (tab.dataset.tab === "videos") loadVideos();
    if (tab.dataset.tab === "tiktok") loadTikToks();
    if (tab.dataset.tab === "ffbb") loadFfbb();
  });
});

// === HELPERS ===
function yesterday() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

function showSpinner() { spinnerEl.hidden = false; }
function hideSpinner() { spinnerEl.hidden = true; }
function showError(msg) { errorEl.textContent = msg; errorEl.hidden = false; }
function hideError() { errorEl.hidden = true; }

// === RENDER GAMES ===
function renderGames(data) {
  gamesDateEl.textContent = data.date;
  gamesListEl.innerHTML = "";

  if (data.games.length === 0) {
    noGamesEl.hidden = false;
    return;
  }
  noGamesEl.hidden = true;

  for (const g of data.games) {
    const homeWin = g.home_score > g.away_score;
    const card = document.createElement("div");
    card.className = "game-card";
    card.innerHTML = `
      <div class="game-score-row">
        <div class="team-info">
          <img class="team-logo" src="${teamLogo(g.home_team)}" alt="${g.home_team}">
          <span class="team-name ${homeWin ? "winner" : ""}">${teamName(g.home_team)}</span>
        </div>
        <div class="score-center">
          <div class="score-value">${g.home_score} — ${g.away_score}</div>
          <div class="score-label">Final</div>
        </div>
        <div class="team-info">
          <img class="team-logo" src="${teamLogo(g.away_team)}" alt="${g.away_team}">
          <span class="team-name ${!homeWin ? "winner" : ""}">${teamName(g.away_team)}</span>
        </div>
      </div>
      <div class="game-quarters">
        Q1: ${g.quarters.home[0]}-${g.quarters.away[0]} &nbsp;|&nbsp;
        Q2: ${g.quarters.home[1]}-${g.quarters.away[1]} &nbsp;|&nbsp;
        Q3: ${g.quarters.home[2]}-${g.quarters.away[2]} &nbsp;|&nbsp;
        Q4: ${g.quarters.home[3]}-${g.quarters.away[3]}
      </div>
      <div class="game-arena">${g.arena}</div>
      <div class="game-players">
        ${g.top_players.map(p =>
          `<div class="player-line">
            <span class="player-star">★</span>
            <span class="player-team-badge">${p.team}</span>
            <span class="player-name">${p.player_name}</span>
            <span class="player-stats">— ${p.points} pts, ${p.rebounds} reb, ${p.assists} ast</span>
          </div>`
        ).join("")}
      </div>
    `;
    gamesListEl.appendChild(card);
  }
}

// === RENDER STANDINGS ===
function renderStandings(teams, container) {
  container.innerHTML = "";
  let lastStatus = null;

  for (const s of teams) {
    if (lastStatus && lastStatus !== s.playoff_status) {
      const hr = document.createElement("hr");
      hr.className = "standings-separator";
      container.appendChild(hr);
    }
    lastStatus = s.playoff_status;

    const row = document.createElement("div");
    const isLeader = s.rank === 1;
    const isOut = s.playoff_status === "out";
    row.className = "standings-row" + (isLeader ? " leader" : "") + (isOut ? " out" : "");

    const badgeClass = s.playoff_status === "playoff" ? "badge-playoff"
      : s.playoff_status === "playin" ? "badge-playin" : "badge-out";
    const badgeLabel = s.playoff_status === "playoff" ? "Playoff"
      : s.playoff_status === "playin" ? "Play-in" : "Out";

    row.innerHTML = `
      <span class="s-rank">${s.rank}</span>
      <img class="s-logo" src="${teamLogoByName(s.team)}" alt="${s.team_abbr}">
      <span class="s-name">${s.team}</span>
      <span class="s-record">${s.wins} — ${s.losses}</span>
      <span class="badge ${badgeClass}">${badgeLabel}</span>
    `;
    container.appendChild(row);
  }
}

// === DATA LOADING ===
async function loadData(dateStr) {
  hideError();
  showSpinner();
  try {
    const [gamesResp, standingsResp] = await Promise.all([
      fetch(`${BASE}/api/games?date=${dateStr}`),
      fetch(`${BASE}/api/standings?date=${dateStr}`),
    ]);

    if (!gamesResp.ok || !standingsResp.ok) {
      throw new Error("Erreur lors du chargement des donnees");
    }

    const gamesData = await gamesResp.json();
    const standingsData = await standingsResp.json();

    renderGames(gamesData);
    renderStandings(standingsData.east, eastStandingsEl);
    renderStandings(standingsData.west, westStandingsEl);
  } catch (err) {
    showError(err.message);
  } finally {
    hideSpinner();
  }
}

async function handleRefresh() {
  refreshBtn.disabled = true;
  refreshBtn.textContent = "...";
  hideError();
  try {
    const resp = await fetch(`${BASE}/api/refresh`, { method: "POST" });
    if (!resp.ok) throw new Error("Echec du rafraichissement");
    await loadData(datePicker.value);
  } catch (err) {
    showError(err.message);
  } finally {
    refreshBtn.disabled = false;
    refreshBtn.textContent = "Rafraichir";
  }
}

// === VIDEOS ===
const videosListEl = document.getElementById("videos-list");
const noVideosEl = document.getElementById("no-videos");
let videosLoaded = false;
let activeVideoId = null;

function renderVideos(data) {
  videosListEl.innerHTML = "";

  if (data.videos.length === 0) {
    noVideosEl.hidden = false;
    return;
  }
  noVideosEl.hidden = true;

  for (const v of data.videos) {
    const card = document.createElement("div");
    card.className = "video-card";
    card.innerHTML = `
      <div class="video-thumbnail" data-video-id="${v.video_id}">
        <img src="${v.thumbnail}" alt="${v.title}">
        <div class="video-play-btn">&#9654;</div>
      </div>
      <div class="video-info">
        <div class="video-title">${v.title}</div>
        <div class="video-date">${new Date(v.published).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" })}</div>
        ${v.description ? `<div class="video-desc">${v.description}</div>` : ""}
      </div>
    `;

    const thumb = card.querySelector(".video-thumbnail");
    thumb.addEventListener("click", () => {
      if (activeVideoId === v.video_id) return;
      // Restaure les autres miniatures
      if (activeVideoId) {
        const prev = videosListEl.querySelector(`[data-active="true"]`);
        if (prev) {
          const prevCard = prev.closest(".video-card");
          const prevData = prev.dataset.videoId;
          prev.removeAttribute("data-active");
          prev.innerHTML = `
            <img src="${prev.dataset.thumb}" alt="">
            <div class="video-play-btn">&#9654;</div>
          `;
        }
      }
      thumb.dataset.active = "true";
      thumb.dataset.thumb = v.thumbnail;
      thumb.innerHTML = `<iframe src="https://www.youtube.com/embed/${v.video_id}?autoplay=1" frameborder="0" allowfullscreen allow="autoplay; encrypted-media"></iframe>`;
      activeVideoId = v.video_id;
    });

    videosListEl.appendChild(card);
  }
}

async function loadVideos() {
  if (videosLoaded) return;
  showSpinner();
  try {
    const resp = await fetch(`${BASE}/api/videos`);
    if (!resp.ok) throw new Error("Erreur chargement videos");
    const data = await resp.json();
    renderVideos(data);
    videosLoaded = true;
  } catch (err) {
    videosListEl.innerHTML = `<p class="empty-message">Impossible de charger les videos</p>`;
  } finally {
    hideSpinner();
  }
}

// === TIKTOK ===
const tiktokListEl = document.getElementById("tiktok-list");
const noTiktokEl = document.getElementById("no-tiktok");
let tiktoksLoaded = false;
let activeTiktokId = null;

function renderTikToks(data) {
  tiktokListEl.innerHTML = "";

  if (data.videos.length === 0) {
    noTiktokEl.hidden = false;
    return;
  }
  noTiktokEl.hidden = true;

  for (const v of data.videos) {
    const card = document.createElement("div");
    card.className = "tiktok-card";
    card.innerHTML = `
      <div class="tiktok-thumbnail" data-video-id="${v.video_id}" data-thumb="${v.thumbnail}">
        <img src="${v.thumbnail}" alt="">
        <div class="video-play-btn">&#9654;</div>
      </div>
      <div class="tiktok-info">
        <div class="tiktok-caption">${v.caption}</div>
        <div class="tiktok-date">${new Date(v.published).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" })}</div>
      </div>
    `;

    const thumb = card.querySelector(".tiktok-thumbnail");
    thumb.addEventListener("click", () => {
      if (activeTiktokId === v.video_id) return;
      // Restaure l'eventuelle miniature precedemment activee
      if (activeTiktokId) {
        const prev = tiktokListEl.querySelector('[data-active="true"]');
        if (prev) {
          prev.removeAttribute("data-active");
          prev.innerHTML = `
            <img src="${prev.dataset.thumb}" alt="">
            <div class="video-play-btn">&#9654;</div>
          `;
        }
      }
      thumb.dataset.active = "true";
      thumb.innerHTML = `<iframe src="https://www.tiktok.com/player/v1/${v.video_id}?rel=0&music_info=0&description=0" allow="autoplay; encrypted-media" allowfullscreen sandbox="allow-scripts allow-same-origin allow-presentation"></iframe>`;
      activeTiktokId = v.video_id;
    });

    tiktokListEl.appendChild(card);
  }
}

async function loadTikToks() {
  if (tiktoksLoaded) return;
  showSpinner();
  try {
    const resp = await fetch(`${BASE}/api/tiktok`);
    if (!resp.ok) throw new Error("Erreur chargement tiktok");
    const data = await resp.json();
    renderTikToks(data);
    tiktoksLoaded = true;
  } catch (err) {
    tiktokListEl.innerHTML = `<p class="empty-message">Impossible de charger les videos TikTok</p>`;
  } finally {
    hideSpinner();
  }
}

// === FFBB ===
const ffbbContentEl = document.getElementById("ffbb-content");
let ffbbLoaded = false;

function formatDate(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

function renderFfbb(data) {
  let html = `
    <div class="ffbb-header">
      <div class="ffbb-team-name">🏀 ${data.team}</div>
      <div class="ffbb-category">${data.category}</div>
    </div>
  `;

  // Classement
  html += `<div class="section-title">Classement</div>`;
  for (const s of data.standings) {
    const diffNum = parseInt(s.diff);
    const diffClass = diffNum > 0 ? "positive" : diffNum < 0 ? "negative" : "";
    const diffPrefix = diffNum > 0 ? "+" : "";
    html += `
      <div class="ffbb-standings-row ${s.is_my_team ? "my-team" : ""}">
        <span class="ffbb-s-rank">${s.rank}</span>
        <span class="ffbb-s-team">${s.team}</span>
        <span class="ffbb-s-pts">${s.pts} pts</span>
        <span class="ffbb-s-record">${s.wins}V ${s.losses}D</span>
        <span class="ffbb-s-diff ${diffClass}">${diffPrefix}${s.diff}</span>
      </div>
    `;
  }

  // Prochain match
  const nextMatch = data.calendar.find(m => !m.played);
  if (nextMatch) {
    const isHome = nextMatch.is_home;
    const opponent = isHome ? nextMatch.away_team : nextMatch.home_team;
    html += `
      <div class="section-title" style="margin-top:20px;">Prochain match</div>
      <div class="ffbb-match upcoming">
        <span class="ffbb-match-journee">J${nextMatch.journee}</span>
        <span class="ffbb-match-date">${formatDate(nextMatch.date)}</span>
        <div class="ffbb-match-teams">
          <span class="my-team-name">Union Du Sillon</span>
          <span style="color:#666;"> vs </span>
          <span style="color:#ccc;">${opponent}</span>
        </div>
        <span class="ffbb-match-score upcoming">${isHome ? "DOM" : "EXT"}</span>
      </div>
    `;
  }

  // Resultats
  const played = data.calendar.filter(m => m.played).reverse();
  if (played.length > 0) {
    html += `<div class="section-title" style="margin-top:20px;">Resultats</div>`;
    for (const m of played) {
      const myScore = m.is_home ? m.home_score : m.away_score;
      const oppScore = m.is_home ? m.away_score : m.home_score;
      const won = myScore > oppScore;
      const statusClass = won ? "win" : "loss";
      html += `
        <div class="ffbb-match ${statusClass}">
          <span class="ffbb-match-journee">J${m.journee}</span>
          <span class="ffbb-match-date">${formatDate(m.date)}</span>
          <div class="ffbb-match-teams">
            <span class="${m.is_home ? "my-team-name" : "home"}">${m.home_team}</span>
            <span style="color:#666;"> — </span>
            <span class="${!m.is_home ? "my-team-name" : "away"}">${m.away_team}</span>
          </div>
          <span class="ffbb-match-score">${m.home_score} - ${m.away_score}</span>
          <span class="ffbb-match-location">${m.is_home ? "DOM" : "EXT"}</span>
        </div>
      `;
    }
  }

  // Matchs a venir
  const upcoming = data.calendar.filter(m => !m.played);
  if (upcoming.length > 1) {
    html += `<div class="section-title" style="margin-top:20px;">A venir</div>`;
    for (const m of upcoming) {
      html += `
        <div class="ffbb-match upcoming">
          <span class="ffbb-match-journee">J${m.journee}</span>
          <span class="ffbb-match-date">${formatDate(m.date)}</span>
          <div class="ffbb-match-teams">
            <span class="${m.is_home ? "my-team-name" : "home"}">${m.home_team}</span>
            <span style="color:#666;"> — </span>
            <span class="${!m.is_home ? "my-team-name" : "away"}">${m.away_team}</span>
          </div>
          <span class="ffbb-match-score upcoming">${m.is_home ? "DOM" : "EXT"}</span>
        </div>
      `;
    }
  }

  ffbbContentEl.innerHTML = html;
}

async function loadFfbb() {
  if (ffbbLoaded) return;
  showSpinner();
  try {
    const resp = await fetch(`${BASE}/api/ffbb`);
    if (!resp.ok) throw new Error("Erreur chargement FFBB");
    const data = await resp.json();
    renderFfbb(data);
    ffbbLoaded = true;
  } catch (err) {
    ffbbContentEl.innerHTML = `<p class="empty-message">Impossible de charger les donnees FFBB</p>`;
  } finally {
    hideSpinner();
  }
}

// === INIT ===
datePicker.value = yesterday();
datePicker.max = yesterday();

datePicker.addEventListener("change", () => loadData(datePicker.value));
refreshBtn.addEventListener("click", handleRefresh);

loadData(datePicker.value);