const $ = (selector) => document.querySelector(selector);
let history = [];
let cursor = 0;
let data = null;
let selected = null;
let requestId = 0;
let stateController = null;
let statsController = null;
let statsTimer = null;
const positionStateCache = new Map();
let engineRequestId = 0;
let engineController = null;
let engineTimer = null;
let enginePaused = false;
let engineRenderedKey = null;
let openingCatalogue = null;
let activeOpening = null;
let activeGuide = null;
let guideRequestId = 0;
let cataloguePath = [];

function formatNumber(value) {
  return value === null || value === undefined ? "—" : new Intl.NumberFormat().format(value);
}
function formatPercent(value) {
  return value === null || value === undefined ? "—" : (value * 100).toFixed(value >= .1 ? 1 : 2) + "%";
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[char]);
}
function threshold() {
  return Number($("#frequency-threshold").value);
}
function thresholdLabel() {
  return (threshold() * 100).toFixed(threshold() < .01 ? 1 : 0) + "%";
}
async function readJsonResponse(response, label) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    await response.text();
    if (response.status === 404) {
      throw new Error(`${label} is not available in the running backend. Close and reopen Chess Memoriser from the application menu.`);
    }
    throw new Error(`${label} returned HTTP ${response.status} instead of data.`);
  }
  try {
    return await response.json();
  } catch (_error) {
    throw new Error(`${label} returned an invalid response. Close and reopen Chess Memoriser.`);
  }
}
function resultBar(move) {
  if (!move || [move.white_wins, move.draws, move.black_wins].some(value => value === null || value === undefined)) {
    return '<span class="result-unavailable">—</span>';
  }
  const total = move.white_wins + move.draws + move.black_wins;
  if (!total) return '<span class="result-unavailable">No results</span>';
  const white = move.white_wins / total * 100;
  const draws = move.draws / total * 100;
  const black = move.black_wins / total * 100;
  const label = `White ${white.toFixed(1)}%, Draw ${draws.toFixed(1)}%, Black ${black.toFixed(1)}%`;
  return `<div class="result" role="img" aria-label="${label}" title="${label}">
    <div class="result-bar">
      <span class="white" style="width:${white}%"></span>
      <span class="draw" style="width:${draws}%"></span>
      <span class="black" style="width:${black}%"></span>
    </div>
    <div class="result-values"><span>W ${white.toFixed(1)}%</span><span>D ${draws.toFixed(1)}%</span><span>B ${black.toFixed(1)}%</span></div>
  </div>`;
}
function fenPieces(fen) {
  const result = {};
  const ranks = fen.split(" ")[0].split("/");
  ranks.forEach((rank, r) => {
    let file = 0;
    for (const char of rank) {
      if (/\d/.test(char)) file += Number(char);
      else { result["abcdefgh"[file] + (8-r)] = char; file++; }
    }
  });
  return result;
}
function legalFrom(square) {
  return (data?.legal_moves || []).filter(move => move.uci.slice(0,2) === square);
}
function play(uci) {
  history = history.slice(0, cursor);
  history.push(uci);
  cursor++;
  selected = null;
  load(true);
}
function loadLine(ucis) {
  history = [...ucis];
  cursor = history.length;
  selected = null;
  load(true);
}
function clickSquare(square) {
  if (!data) return;
  if (selected) {
    const targets = legalFrom(selected).filter(move => move.uci.slice(2,4) === square);
    if (targets.length === 1) {
      play(targets[0].uci);
      return;
    }
    if (targets.length > 1) {
      const options = $("#promotion-options");
      options.replaceChildren(...targets.map(move => {
        const button = document.createElement("button");
        button.textContent = move.san;
        button.onclick = () => { $("#promotion").close(); play(move.uci); };
        return button;
      }));
      $("#promotion").showModal();
      return;
    }
  }
  selected = legalFrom(square).length ? square : null;
  renderBoard();
}
function renderBoard() {
  const grid = $("#grid");
  grid.replaceChildren();
  if (!data) return;
  const map = fenPieces(data.position.fen);
  const targets = new Set(selected ? legalFrom(selected).map(move => move.uci.slice(2,4)) : []);
  for (let rank = 8; rank >= 1; rank--) {
    for (let file = 0; file < 8; file++) {
      const square = "abcdefgh"[file] + rank;
      const button = document.createElement("button");
      button.className = `sq ${(file + rank) % 2 ? "dark" : "light"}`;
      if (selected === square) button.classList.add("selected");
      if (targets.has(square)) button.classList.add("target");
      if (map[square]) button.classList.add("occupied");
      if (map[square]) {
        const piece = document.createElement("img");
        piece.className = "piece";
        piece.src = `/ui/piece-alpha-${map[square] === map[square].toUpperCase() ? "w" : "b"}${map[square].toUpperCase()}.svg`;
        piece.alt = map[square];
        piece.draggable = false;
        button.append(piece);
      }
      button.setAttribute("aria-label", square + (map[square] ? ` ${map[square]}` : ""));
      button.onclick = () => clickSquare(square);
      if (file === 7) {
        const coord = document.createElement("span");
        coord.className = "coord rank-coordinate";
        coord.textContent = rank;
        button.append(coord);
      }
      if (rank === 1) {
        const coord = document.createElement("span");
        coord.className = "coord file-coordinate";
        coord.textContent = "abcdefgh"[file];
        button.append(coord);
      }
      grid.append(button);
    }
  }
}
function statusText(source, kind) {
  const el = $(`#${kind}-status`);
  if (!el) return;
  if (!source.available) {
    el.textContent = "Unavailable"; el.classList.add("error"); return;
  }
  el.classList.remove("error");
  if (kind === "lichess") {
    const origin = source.metadata.cache_origin;
    el.textContent = origin === "live_api" ? "Live · cached now" : origin === "local_cache" ? "Local cache" : "Reused legacy cache";
  } else el.textContent = "Complete local index";
}
function renderSources() {
  const lichess = data.distributions.lichess_player_games;
  const master = data.distributions.installed_master_database;
  $("#lichess-total").textContent = formatNumber(lichess.position_games);
  const masterTotal = $("#master-total");
  if (masterTotal) masterTotal.textContent = formatNumber(master.position_games);
  statusText(lichess, "lichess"); statusText(master, "master");
  const failures = [lichess, master].filter(source => !source.available).flatMap(source => source.limitations);
  const notice = $("#notice");
  notice.textContent = failures.join(" · ");
  notice.classList.toggle("hidden", !failures.length);
}
function renderMoves() {
  const body = $("#moves"); body.replaceChildren();
  const lichess = data.distributions.lichess_player_games;
  const master = data.distributions.installed_master_database;
  const byUci = new Map();
  for (const move of data.legal_moves) byUci.set(move.uci, {uci:move.uci, san:move.san});
  const minimum = threshold();
  const label = thresholdLabel();
  const masterSourceName = $("#master-source-name");
  if (masterSourceName) masterSourceName.textContent = `Lumbra OTB · both 2200+ · display ≥${label}`;
  $("#lichess-source-name").textContent = `Lichess players · display ≥${label}`;
  $("#master-table-head").textContent = `OTB 2200+ · ≥${label}`;
  $("#lichess-table-head").textContent = `Lichess players · ≥${label}`;
  for (const move of lichess.moves) {
    if (move.frequency !== null && move.frequency >= minimum) {
      Object.assign(byUci.get(move.uci) || {}, {uci:move.uci, san:move.san, lichess:move});
    }
  }
  for (const move of master.moves) {
    if (move.frequency !== null && move.frequency >= minimum) {
      Object.assign(byUci.get(move.uci) || {}, {uci:move.uci, san:move.san, master:move});
    }
  }
  const rows = [...byUci.values()].filter(row => row.lichess || row.master)
    .sort((a,b) => (b.master?.games || 0) - (a.master?.games || 0) || (b.lichess?.games || 0) - (a.lichess?.games || 0));
  if (!rows.length) {
    const row = document.createElement("tr"); row.innerHTML = '<td colspan="7" class="missing">No recorded continuations</td>'; body.append(row); return;
  }
  for (const item of rows) {
    const row = document.createElement("tr");
    row.innerHTML = `<td>${item.san}</td>
      <td>${formatNumber(item.master?.games)}</td><td class="pct">${formatPercent(item.master?.frequency)}</td><td>${resultBar(item.master)}</td>
      <td>${formatNumber(item.lichess?.games)}</td><td class="pct">${formatPercent(item.lichess?.frequency)}</td><td>${resultBar(item.lichess)}</td>`;
    row.onclick = () => play(item.uci); body.append(row);
  }
}
function renderLine() {
  const line = $("#line"); line.replaceChildren();
  if (!history.length) { line.innerHTML = '<span class="empty">Starting position</span>'; return; }
  const sans = data.position.san_sequence;
  history.forEach((uci, index) => {
    const button = document.createElement("button"); button.className = "ply" + (index === cursor-1 ? " current" : "");
    button.textContent = index < sans.length ? sans[index] : (index + 1 <= cursor ? uci : "· " + uci);
    button.onclick = () => { cursor = index + 1; selected = null; load(true); }; line.append(button);
  });
}
function sourceMove(source, uci) {
  if (!source?.available) return null;
  return source.moves.find(move => move.uci === uci) || {games: 0, frequency: 0};
}
function guideStat(source, uci) {
  if (!source?.available) return "unavailable";
  const move = sourceMove(source, uci);
  return `${formatPercent(move.frequency)} · ${formatNumber(move.games)} games`;
}
function currentFilterText() {
  const rating = $("#ratings").selectedOptions[0].textContent;
  const speeds = $("#speeds").selectedOptions[0].textContent;
  return `${rating} · ${speeds}`;
}
function taxonomySearchText(node, openingBySlug) {
  const linked = node.opening_slugs.flatMap(slug => {
    const opening = openingBySlug.get(slug);
    return opening ? [opening.name, ...opening.aliases, ...opening.eco, opening.eco_family] : [];
  });
  return [node.label, ...linked].join(" ").toLowerCase();
}
function flattenTaxonomy(nodes) {
  const result = [];
  const visit = (node, path) => {
    result.push({node, path});
    node.children.forEach((child, index) => visit(child, [...path, index]));
  };
  nodes.forEach((node, index) => visit(node, [index]));
  return result;
}
function sameMovePrefix(prefix, line) {
  return prefix.length <= line.length && prefix.every((move, index) => line[index] === move);
}
function wikiTaxonomy() {
  if (!openingCatalogue) return [];
  return flattenTaxonomy(openingCatalogue.hierarchy_draft.roots)
    .filter(({node}) => node.level !== "position")
    .map(item => {
      const parent = item.path.length > 1 ? taxonomyNodeAt(item.path.slice(0, -1)) : null;
      const line = item.node.position_data.moves_uci;
      const parentLine = parent?.position_data.moves_uci || [];
      const isContainer = Boolean(parent && line.length === parentLine.length && line.every((move, index) => parentLine[index] === move));
      const pathKey = item.path.map((index, depth) => {
      let nodes = openingCatalogue.hierarchy_draft.roots;
      let node = null;
      for (const step of item.path.slice(0, depth + 1)) {
        node = nodes[step];
        nodes = node.children;
      }
      return node.label;
      }).join("/");
      return {...item, pathKey, isContainer};
    });
}
function wikiArticleFor(pathKey) {
  const entries = openingCatalogue?.wiki?.entries || {};
  const parts = pathKey ? pathKey.split("/") : [];
  while (parts.length) {
    const key = parts.join("/");
    if (entries[key]) return {article: entries[key], sourcePath: key};
    parts.pop();
  }
  return {article: openingCatalogue?.wiki?.home, sourcePath: ""};
}
function currentWikiClassification(items) {
  const moves = history.slice(0, cursor);
  if (!moves.length) return {matches: [], primary: null};
  const exactPosition = items.filter(({node, isContainer}) => !isContainer && node.position_data.position_key === data?.position?.position_key);
  const reached = items.filter(({node, isContainer}) => {
    if (isContainer) return false;
    const line = node.position_data.moves_uci;
    return line.length && line.length <= moves.length && sameMovePrefix(line, moves);
  });
  const pool = exactPosition.length ? exactPosition : reached;
  pool.sort((a, b) => b.node.position_data.moves_uci.length - a.node.position_data.moves_uci.length || b.path.length - a.path.length);
  const primary = pool[0] || null;
  const matches = pool.filter(item => item.node.position_data.position_key === primary?.node.position_data.position_key);
  return {matches, primary};
}
function wikiMoveRows(items) {
  if (!data) return [];
  const moves = history.slice(0, cursor);
  const legal = new Map(data.legal_moves.map(move => [move.uci, move]));
  const groups = new Map();
  for (const item of items) {
    const line = item.node.position_data.moves_uci;
    if (line.length <= moves.length || !sameMovePrefix(moves, line)) continue;
    const uci = line[moves.length];
    if (!legal.has(uci)) continue;
    if (!groups.has(uci)) groups.set(uci, []);
    groups.get(uci).push(item);
  }
  const master = data.distributions?.installed_master_database;
  const lichess = data.distributions?.lichess_player_games;
  const result = [];
  const routeLabels = {
    "e2e4,c7c5|g1f3": "Open Sicilian routes",
  };
  for (const [uci, linked] of groups) {
    const exact = linked.filter(item => !item.isContainer && item.node.position_data.moves_uci.length === moves.length + 1);
    const routeLabel = routeLabels[`${moves.join(",")}|${uci}`];
    const labels = routeLabel ? [routeLabel] : exact.length
      ? exact.map(item => {
          const match = wikiArticleFor(item.pathKey);
          return match.sourcePath === item.pathKey ? match.article?.title : item.node.label;
        }).filter((label, index, all) => all.indexOf(label) === index).slice(0, 2)
      : [linked.length === 1 ? linked[0].node.label : `${linked.length} mapped theory routes`];
    result.push({
      uci,
      san: legal.get(uci).san,
      labels,
      master: sourceMove(master, uci),
      lichess: sourceMove(lichess, uci),
      known: true,
    });
  }
  if (!result.length && data.distributions) {
    const seen = new Set();
    for (const move of [...(master?.moves || []), ...(lichess?.moves || [])]) {
      if (!legal.has(move.uci) || seen.has(move.uci)) continue;
      seen.add(move.uci);
      result.push({
        uci: move.uci,
        san: legal.get(move.uci).san,
        labels: ["Database continuation"],
        master: sourceMove(master, move.uci),
        lichess: sourceMove(lichess, move.uci),
        known: false,
      });
    }
  }
  return result.sort((a, b) =>
    (b.master?.games || 0) - (a.master?.games || 0) ||
    (b.lichess?.games || 0) - (a.lichess?.games || 0) ||
    a.san.localeCompare(b.san)
  ).slice(0, 10);
}
function renderOpeningWiki() {
  if (!openingCatalogue || !data || !$("#wiki-article")) return;
  const items = wikiTaxonomy();
  const classification = currentWikiClassification(items);
  const pathKey = classification.primary?.pathKey || "";
  const {article, sourcePath} = wikiArticleFor(pathKey);
  const title = classification.primary && sourcePath !== pathKey
    ? classification.primary.node.label
    : article.title;
  const trail = pathKey ? pathKey.split("/") : ["Starting position"];
  const related = classification.matches
    .map(item => item.node.label)
    .filter((label, index, all) => label !== classification.primary?.node.label && all.indexOf(label) === index);
  const sources = (article.sources || []).map(source =>
    `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.label)} ↗</a>`
  ).join("");
  $("#wiki-article").innerHTML = `
    <div class="wiki-trail">${trail.map(part => `<span>${escapeHtml(part)}</span>`).join("")}</div>
    <span class="wiki-kicker">${classification.primary ? "Current opening family" : "Starting position"}</span>
    <h2>${escapeHtml(title)}</h2>
    ${classification.primary && sourcePath !== pathKey ? `<p class="wiki-inherits">High-level context: ${escapeHtml(article.title)}</p>` : ""}
    <p class="wiki-summary">${escapeHtml(article.summary)}</p>
    ${(article.ideas || []).length ? `<ul>${article.ideas.map(idea => `<li>${escapeHtml(idea)}</li>`).join("")}</ul>` : ""}
    ${related.length ? `<div class="wiki-related"><b>Also recognised as</b>${related.map(name => `<span>${escapeHtml(name)}</span>`).join("")}</div>` : ""}
    <div class="wiki-sources"><b>Sources</b>${sources}</div>`;

  const rows = wikiMoveRows(items);
  const movesPanel = $("#wiki-moves");
  movesPanel.replaceChildren();
  if (!rows.length) {
    movesPanel.innerHTML = '<span class="empty">No mapped theory moves from this position.</span>';
  } else {
    rows.forEach((row, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "wiki-move" + (row.known ? " known" : "");
      button.innerHTML = `<span class="wiki-rank">${index + 1}</span><strong>${escapeHtml(row.san)}</strong>
        <span class="wiki-move-name">${escapeHtml(row.labels.join(" · "))}</span>
        <span class="wiki-frequency"><i>OTB ${formatPercent(row.master?.frequency)}</i><i>Lichess ${formatPercent(row.lichess?.frequency)}</i></span>`;
      button.onclick = () => play(row.uci);
      movesPanel.append(button);
    });
  }
  $("#catalogue-count").textContent = classification.primary ? classification.primary.node.label : "Start";
}
function taxonomyNodeAt(path) {
  let nodes = openingCatalogue.hierarchy_draft.roots;
  let node = null;
  for (const index of path) {
    node = nodes[index];
    if (!node) return null;
    nodes = node.children;
  }
  return node;
}
function miniBoard(fen) {
  const board = document.createElement("div");
  board.className = "mini-board";
  board.setAttribute("aria-label", `Position: ${fen}`);
  const pieces = fenPieces(fen);
  for (let rank = 8; rank >= 1; rank--) {
    for (let file = 0; file < 8; file++) {
      const square = document.createElement("span");
      square.className = "mini-square";
      const pieceCode = pieces["abcdefgh"[file] + rank];
      if (pieceCode) {
        const piece = document.createElement("img");
        piece.src = `/ui/piece-alpha-${pieceCode === pieceCode.toUpperCase() ? "w" : "b"}${pieceCode.toUpperCase()}.svg`;
        piece.alt = "";
        piece.draggable = false;
        square.append(piece);
      }
      board.append(square);
    }
  }
  return board;
}
function browseTaxonomy(path) {
  cataloguePath = [...path];
  $("#opening-search").value = "";
  $("#opening-group").value = path.length ? String(path[0]) : "";
  renderOpeningCatalogue();
}
function taxonomyCard(node, path, openingBySlug) {
  const card = document.createElement("article");
  card.className = `opening-map-card level-${node.level}`;
  const isKeyPosition = node.level === "position";
  const displayedPosition = isKeyPosition ? node.position_data : node.mainline_position_data;
  const displayedPgn = isKeyPosition ? node.pgn : node.mainline_pgn;
  card.append(miniBoard(displayedPosition.fen));
  const content = document.createElement("div");
  content.className = "opening-map-content";
  content.innerHTML = `<span class="opening-map-level">${escapeHtml(node.level)}</span><h3>${escapeHtml(node.label)}</h3>`;
  if (!isKeyPosition && node.mainline_pgn !== node.pgn) {
    const definition = document.createElement("p");
    definition.className = "opening-map-definition";
    definition.textContent = `Defines: ${node.pgn}`;
    definition.title = definition.textContent;
    content.append(definition);
  }
  const pgn = document.createElement("button");
  pgn.type = "button";
  pgn.className = "opening-map-pgn";
  pgn.title = `Load ${displayedPgn}`;
  pgn.innerHTML = `<span>${isKeyPosition ? "Key position" : "Database mainline trunk"}</span><strong>${escapeHtml(displayedPgn)}</strong>`;
  pgn.onclick = () => loadLine(displayedPosition.moves_uci);
  content.append(pgn);
  const stopLabels = {
    wide_choice: "Choice point",
    small_sample: "Low OTB coverage",
    middlegame_depth: "Middlegame",
    no_continuations: "End of data",
    definition_only: "Defining position",
  };
  if (!isKeyPosition) {
    const stop = document.createElement("span");
    stop.className = "opening-map-stop";
    const games = node.mainline_stop_games === null ? "" : ` · ${formatNumber(node.mainline_stop_games)} OTB games`;
    stop.textContent = `${stopLabels[node.mainline_stop_reason] || "Stop position"}${games}`;
    content.append(stop);
    if (node.mainline_choices.length) {
      const branches = document.createElement("div");
      branches.className = "opening-map-branches";
      branches.innerHTML = `<b>Next</b>${node.mainline_choices.slice(0, 3).map(choice =>
        `<span>${escapeHtml(choice.san)} <i>${formatPercent(choice.frequency)}</i></span>`
      ).join("")}`;
      content.append(branches);
    }
  }
  if (node.sidelines?.length) {
    const sidelines = document.createElement("details");
    sidelines.className = "opening-map-sidelines";
    sidelines.innerHTML = `<summary>${node.sidelines.length} TACTICAL SIDELINE${node.sidelines.length === 1 ? "" : "S"}</summary>`;
    node.sidelines.forEach(sideline => {
      const button = document.createElement("button");
      button.type = "button";
      button.innerHTML = `<b>${escapeHtml(sideline.label)}</b><span>${escapeHtml(sideline.pgn)}</span>`;
      button.onclick = () => loadLine(sideline.position_data.moves_uci);
      sidelines.append(button);
    });
    content.append(sidelines);
  }
  const actions = document.createElement("div");
  actions.className = "opening-map-actions";
  if (node.children.length) {
    const browse = document.createElement("button");
    browse.type = "button";
    browse.className = "opening-map-browse";
    const childLabel = node.child_role === "key_positions"
      ? `KEY POSITION${node.children.length === 1 ? "" : "S"}`
      : (node.children.length === 1 ? "Option" : "Options");
    browse.textContent = `BROWSE ${node.children.length} ${childLabel} →`;
    browse.onclick = () => browseTaxonomy(path);
    actions.append(browse);
  } else {
    const loadPosition = document.createElement("button");
    loadPosition.type = "button";
    loadPosition.className = "opening-map-browse";
    loadPosition.textContent = "Load on board";
    loadPosition.onclick = () => loadLine(displayedPosition.moves_uci);
    actions.append(loadPosition);
  }
  const opening = node.opening_slugs.length ? openingBySlug.get(node.opening_slugs[0]) : null;
  if (opening?.guide_available) {
    const guide = document.createElement("button");
    guide.type = "button";
    guide.className = "opening-map-guide";
    guide.textContent = "Strategic guide";
    guide.onclick = () => selectOpening(opening.slug);
    actions.append(guide);
  }
  content.append(actions);
  card.append(content);
  return card;
}
function renderOpeningCatalogue() {
  if (!openingCatalogue) return;
  const query = $("#opening-search").value.trim().toLowerCase();
  const openingBySlug = new Map(openingCatalogue.openings.map(opening => [opening.slug, opening]));
  let cards;
  let heading;
  if (query) {
    cards = flattenTaxonomy(openingCatalogue.hierarchy_draft.roots)
      .filter(({node}) => taxonomySearchText(node, openingBySlug).includes(query));
    heading = `Search results for “${$("#opening-search").value.trim()}”`;
    $("#catalogue-count").textContent = `${cards.length} RESULTS`;
  } else {
    const parent = taxonomyNodeAt(cataloguePath);
    const nodes = parent ? parent.children : openingCatalogue.hierarchy_draft.roots;
    cards = nodes.map((node, index) => ({node, path: [...cataloguePath, index]}));
    heading = parent ? parent.label : "Opening families";
    $("#catalogue-count").textContent = `${cards.length} CHOICES`;
  }
  const list = $("#opening-list");
  list.replaceChildren();
  const nav = document.createElement("div");
  nav.className = "opening-map-nav";
  const home = document.createElement("button");
  home.type = "button";
  home.textContent = "All openings";
  home.onclick = () => browseTaxonomy([]);
  nav.append(home);
  if (!query) {
    cataloguePath.forEach((_, depth) => {
      const node = taxonomyNodeAt(cataloguePath.slice(0, depth + 1));
      const crumb = document.createElement("button");
      crumb.type = "button";
      crumb.textContent = node.label;
      crumb.onclick = () => browseTaxonomy(cataloguePath.slice(0, depth + 1));
      nav.append(crumb);
    });
  }
  const title = document.createElement("h2");
  title.className = "opening-map-title";
  title.textContent = heading;
  list.append(nav, title);
  if (!cards.length) {
    list.innerHTML = '<span class="empty">No categories match this search.</span>';
    return;
  }
  const grid = document.createElement("div");
  grid.className = "opening-map-grid";
  cards.forEach(({node, path}) => grid.append(taxonomyCard(node, path, openingBySlug)));
  list.append(grid);
}
function optionStats(option, decision) {
  const exact = data?.position?.position_key === decision.position_data.position_key;
  if (!exact) return '<span class="choice-stats-away">Load this decision to show its current frequencies</span>';
  if (!data?.distributions) return '<span class="choice-stats-away">Loading exact-position frequencies…</span>';
  const master = data.distributions.installed_master_database;
  const lichess = data.distributions.lichess_player_games;
  return `<span><b>OTB</b> ${guideStat(master, option.move_uci)}</span><span><b>Lichess</b> ${guideStat(lichess, option.move_uci)}</span>`;
}
function lineButton(line, label) {
  const ucis = line.position_data.moves_uci.join(",");
  return `<button class="guide-load line-load" data-line="${ucis}" type="button"><strong>${escapeHtml(label)}</strong><span>${escapeHtml(line.position_data.moves_san.join(" "))}</span></button>`;
}
function bindGuideActions() {
  document.querySelectorAll(".guide-load[data-line]").forEach(button => {
    button.onclick = () => loadLine(button.dataset.line ? button.dataset.line.split(",") : []);
  });
  document.querySelectorAll(".related-opening[data-slug]").forEach(button => {
    button.onclick = () => selectOpening(button.dataset.slug);
  });
  const back = $("#catalogue-back");
  if (back) back.onclick = showCatalogue;
}
function renderOpeningGuide() {
  if (!activeOpening) return;
  const panel = $("#opening-guide");
  if (!activeGuide) {
    panel.innerHTML = `<div class="guide-toolbar"><button id="catalogue-back" type="button">← ALL OPENINGS</button></div>
      <div class="guide-hero"><span class="guide-kicker">${escapeHtml(activeOpening.group)} · ${escapeHtml(activeOpening.eco_family)}</span>
      <h2>${escapeHtml(activeOpening.name)}</h2><p>${escapeHtml(activeOpening.moves_san.join(" "))}</p></div>
      <div class="guide-unavailable"><strong>Detailed guide not built yet</strong><p>The validated defining position is loaded on the board. The unrestricted database explorer and engine remain available below.</p></div>`;
    bindGuideActions();
    return;
  }
  const guide = activeGuide;
  const aliases = guide.aliases.length ? `<p class="guide-aliases">Also: ${escapeHtml(guide.aliases.join(" · "))}</p>` : "";
  const choiceButton = (option, decision, minor=false) => `<button class="guide-choice guide-load${minor ? " minor" : ""}" data-line="${option.line_uci.join(",")}" type="button">
    <span class="choice-title"><b>${escapeHtml(option.move)}</b><strong>${escapeHtml(option.label)}</strong></span>
    <span class="choice-explanation">${escapeHtml(option.explanation)}</span>
    <span class="choice-change">${escapeHtml(option.changes)}</span>
    <span class="choice-stats">${optionStats(option, decision)}</span>
  </button>`;
  const decisions = guide.decisions.map(decision => {
    const exact = data?.position?.position_key === decision.position_data.position_key;
    const core = decision.options.filter(option => option.prominence !== "practical_sideline");
    const minor = decision.options.filter(option => option.prominence === "practical_sideline");
    const options = core.map(option => choiceButton(option, decision)).join("");
    const minorOptions = minor.length ? `<details class="minor-options"><summary>${minor.length} practical sideline${minor.length > 1 ? "s" : ""} · under 1% in local OTB</summary><div>${minor.map(option => choiceButton(option, decision, true)).join("")}</div></details>` : "";
    return `<article class="guide-decision${exact ? " current" : ""}">
      <div class="decision-head"><div><span class="side-badge ${decision.side.toLowerCase()}">${escapeHtml(decision.side)}'s options</span><h3>${escapeHtml(decision.title)}</h3></div>
      <button class="guide-load decision-position" data-line="${decision.position_data.moves_uci.join(",")}" type="button">${exact ? "On board" : "Load decision"}</button></div>
      <p>${escapeHtml(decision.why_here)}</p><div class="guide-choices">${options}</div>${minorOptions}
    </article>`;
  }).join("");
  const mainlines = guide.lines.filter(line => line.category === "mainline").map(line => `<article class="guide-line-card useful-position${line.primary ? " primary-line" : ""}">${line.primary ? '<span class="mainline-badge">Primary main line</span>' : ""}${lineButton(line, line.name)}<p>${escapeHtml(line.result)}</p><div class="plan-grid"><div><b>White's plan</b><ul>${line.white_plans.map(plan => `<li>${escapeHtml(plan)}</li>`).join("")}</ul></div><div><b>Black's plan</b><ul>${line.black_plans.map(plan => `<li>${escapeHtml(plan)}</li>`).join("")}</ul></div></div></article>`).join("");
  const sidelines = guide.lines.filter(line => line.category === "sideline").map(line => `<details class="sideline-row"><summary><strong>${escapeHtml(line.name)}</strong><span>${escapeHtml(line.position_data.moves_san.join(" "))}</span></summary><div class="sideline-body"><button class="guide-load" data-line="${line.position_data.moves_uci.join(",")}" type="button">Load position</button><p>${escapeHtml(line.result)}</p><div class="plan-grid"><div><b>White</b><ul>${line.white_plans.map(plan => `<li>${escapeHtml(plan)}</li>`).join("")}</ul></div><div><b>Black</b><ul>${line.black_plans.map(plan => `<li>${escapeHtml(plan)}</li>`).join("")}</ul></div></div></div></details>`).join("");
  const transpositions = guide.transpositions.map(item => `<article class="transposition-card">${lineButton(item, item.label)}<p>${escapeHtml(item.note)}</p></article>`).join("");
  const related = (guide.related_openings || []).map(slug => {
    const opening = openingCatalogue.openings.find(item => item.slug === slug);
    return opening ? `<button class="related-opening" data-slug="${slug}" type="button">${escapeHtml(opening.name)}</button>` : "";
  }).join("");
  const sources = guide.sources.map(source => `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.label)}</a>`).join("");
  panel.innerHTML = `<div class="guide-toolbar"><button id="catalogue-back" type="button">← ALL OPENINGS</button><span>LIVE CHOICE DATA · ${escapeHtml(currentFilterText())}</span></div>
    <div class="guide-hero"><span class="guide-kicker">PILOT GUIDE · ${escapeHtml(guide.eco)}</span><h2>${escapeHtml(guide.title)}</h2>${aliases}<p>${escapeHtml(guide.summary)}</p>
      <button class="guide-load defining-position" data-line="${guide.defining_position.moves_uci.join(",")}" type="button">LOAD DEFINING POSITION · ${escapeHtml(guide.defining_position.moves_san.join(" "))}</button></div>
    <details class="guide-overview" open><summary>Strategic contest</summary><div class="overview-grid"><div><h3>What the game is about</h3><ul>${guide.strategic_contest.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div><div><h3>Characteristic structures</h3><ul>${guide.structures.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div></div></details>
    <section class="guide-section useful-section"><div class="section-title"><span>Strategic positions</span><h2>Reach a useful position</h2><p>Choose a structure, load it on the board, then use the plans as the position's map.</p></div><div class="useful-position-grid">${mainlines}</div></section>
    <section class="guide-section decision-section"><div class="section-title"><span>Compact choice map</span><h2>Key forks on the way</h2></div><div class="decision-grid">${decisions}</div></section>
    <details class="guide-section guide-sidelines"><summary><span>Common sidelines</span><strong>${guide.lines.filter(line => line.category === "sideline").length} practical deviations</strong></summary><div class="sideline-list">${sidelines}</div></details>
    <section class="guide-section"><div class="section-title"><span>Transpositions</span><h2>Same ideas, different routes</h2></div><div class="transposition-grid">${transpositions}</div>${related ? `<div class="related-row"><b>Related openings</b>${related}</div>` : ""}</section>
    <details class="guide-sources"><summary>SOURCES & SELECTION METHOD</summary><p>${escapeHtml(openingCatalogue.selection_criteria.database_rule)} ${escapeHtml(openingCatalogue.selection_criteria.theory_exception)}</p><div>${sources}</div></details>`;
  bindGuideActions();
}
function showCatalogue() {
  activeOpening = null;
  activeGuide = null;
  guideRequestId++;
  $("#opening-guide").classList.add("hidden");
  $("#opening-browser").classList.remove("hidden");
  renderOpeningCatalogue();
}
async function selectOpening(slug) {
  const opening = openingCatalogue?.openings.find(item => item.slug === slug);
  if (!opening) return;
  activeOpening = opening;
  activeGuide = null;
  $("#opening-browser").classList.add("hidden");
  $("#opening-guide").classList.remove("hidden");
  $("#opening-guide").innerHTML = '<span class="empty">Loading guide…</span>';
  loadLine(opening.moves_uci);
  if (!opening.guide_available) {
    renderOpeningGuide();
    return;
  }
  const id = ++guideRequestId;
  try {
    const response = await fetch(`/api/openings/${encodeURIComponent(slug)}`);
    const payload = await readJsonResponse(response, "Opening guide");
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    if (id !== guideRequestId || activeOpening?.slug !== slug) return;
    activeGuide = payload;
    renderOpeningGuide();
  } catch (error) {
    if (id !== guideRequestId) return;
    $("#opening-guide").innerHTML = `<div class="guide-unavailable"><strong>Guide unavailable</strong><p>${escapeHtml(error.message)}</p></div>`;
  }
}
async function initOpenings() {
  try {
    const response = await fetch("/api/openings");
    const payload = await readJsonResponse(response, "Opening catalogue");
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    openingCatalogue = payload;
    renderOpeningWiki();
  } catch (error) {
    $("#wiki-article").innerHTML = `<span class="engine-error">${escapeHtml(error.message)}</span>`;
    $("#wiki-moves").innerHTML = '<span class="empty">Opening moves unavailable.</span>';
    $("#catalogue-count").textContent = "Unavailable";
  }
}
function engineScore(evaluation) {
  if (!evaluation || evaluation.value === null || evaluation.value === undefined) return "—";
  if (evaluation.unit === "mate") return (evaluation.value >= 0 ? "+" : "−") + "M" + Math.abs(evaluation.value);
  const pawns = evaluation.value / 100;
  return (pawns >= 0 ? "+" : "−") + Math.abs(pawns).toFixed(2);
}
function renderEngine(payload) {
  if (!data || payload.position_key !== data.position.position_key) return;
  const lines = $("#engine-lines");
  lines.replaceChildren();
  if (payload.terminal) {
    lines.innerHTML = '<span class="empty">Terminal position</span>';
  } else if (!payload.lines.length) {
    lines.innerHTML = '<span class="empty">No engine lines</span>';
  } else {
    for (const item of payload.lines) {
      const button = document.createElement("button");
      button.className = "engine-line";
      button.title = "Play " + item.first_move_san;
      const score = document.createElement("strong");
      score.className = "engine-score";
      score.textContent = engineScore(item.evaluation);
      const pv = document.createElement("span");
      pv.className = "engine-pv";
      pv.textContent = item.san.join(" ");
      button.append(score, pv);
      button.onclick = () => play(item.first_move_uci);
      lines.append(button);
    }
  }
  const color = payload.perspective_color || "white";
  $("#engine-perspective").textContent = `Stockfish · ${color} perspective`;
  $("#engine-status").textContent = payload.engine + " · depth " + payload.depth;
}
function cancelEngine(status="Waiting") {
  engineRequestId++;
  clearTimeout(engineTimer);
  engineController?.abort();
  engineController = null;
  $("#engine-status").textContent = status;
}
function clearEngineForPosition() {
  cancelEngine("Waiting for position");
  $("#engine-perspective").textContent = "Stockfish · White perspective";
  $("#engine-lines").innerHTML = '<span class="empty">Updating board position…</span>';
}
function scheduleEngine() {
  cancelEngine(enginePaused ? "Paused" : "Queued");
  if (enginePaused || !data) return;
  const id = engineRequestId;
  const key = [
    history.slice(0, cursor).join(","),
    $("#engine-depth").value,
    $("#engine-multipv").value,
  ].join("|");
  engineTimer = setTimeout(async () => {
    if (id !== engineRequestId || enginePaused) return;
    $("#engine-status").textContent = "Analysing";
    engineController = new AbortController();
    const params = new URLSearchParams({
      moves: history.slice(0, cursor).join(","),
      depth: $("#engine-depth").value,
      multipv: $("#engine-multipv").value,
    });
    try {
      const response = await fetch("/api/engine?" + params, {signal: engineController.signal});
      const payload = await readJsonResponse(response, "Stockfish analysis");
      if (!response.ok) throw new Error(payload.error || "HTTP " + response.status);
      if (id !== engineRequestId || payload.position_key !== data?.position?.position_key) return;
      engineRenderedKey = key;
      renderEngine(payload);
    } catch (error) {
      if (error.name === "AbortError" || id !== engineRequestId) return;
      $("#engine-status").textContent = "Unavailable";
      const lines = $("#engine-lines");
      lines.replaceChildren();
      const message = document.createElement("span");
      message.className = "engine-error";
      message.textContent = error.message;
      lines.append(message);
    }
  }, 280);
}
function renderPosition() {
  $("#turn").textContent = data.position.turn[0].toUpperCase() + data.position.turn.slice(1) + " to move";
  $("#back").disabled = cursor === 0;
  $("#forward").disabled = cursor >= history.length;
  renderBoard();
  renderLine();
  renderOpeningWiki();
}
function render() {
  renderPosition();
  if (!data.distributions) return;
  renderSources();
  renderMoves();
  renderOpeningWiki();
  const l = data.distributions.lichess_player_games, m = data.distributions.installed_master_database;
  $("#position-meta").textContent = `${data.position.position_key} · Lichess denominator ${formatNumber(l.continuation_games)} · OTB denominator ${formatNumber(m.continuation_games)}`;
}
function showStatisticsLoading() {
  for (const kind of ["lichess", "master"]) {
    const status = $(`#${kind}-status`);
    if (!status) continue;
    status.textContent = "Loading";
    status.classList.remove("error");
  }
  $("#lichess-total").textContent = "—";
  const masterTotal = $("#master-total");
  if (masterTotal) masterTotal.textContent = "—";
  $("#moves").innerHTML = '<tr><td colspan="7" class="missing">Loading statistics for this position…</td></tr>';
  $("#position-meta").textContent = data?.position?.position_key || "Loading position…";
  $("#notice").classList.add("hidden");
}
function stateCacheKey(moves) {
  return moves.join(",");
}
function applyPositionState(state, id) {
  if (id !== requestId) return;
  data = {...state, distributions: null};
  selected = null;
  renderPosition();
  showStatisticsLoading();
  $("#engine-perspective").textContent = "Stockfish · White perspective";
  $("#engine-lines").innerHTML = `<span class="empty">Waiting to analyse ${data.position.turn} to move…</span>`;
  scheduleEngine();
  scheduleStatistics(id);
}
function scheduleStatistics(id, delay=120) {
  clearTimeout(statsTimer);
  statsController?.abort();
  statsController = null;
  statsTimer = setTimeout(async () => {
    if (id !== requestId || !data) return;
    const expectedKey = data.position.position_key;
    const params = new URLSearchParams({
      moves: history.slice(0,cursor).join(","), ratings: $("#ratings").value, speeds: $("#speeds").value
    });
    statsController = new AbortController();
    try {
      const response = await fetch("/api/position?" + params, {signal: statsController.signal});
      const payload = await readJsonResponse(response, "Position statistics");
      if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
      if (id !== requestId || payload.position.position_key !== expectedKey || data?.position?.position_key !== expectedKey) return;
      data = payload;
      render();
    } catch (error) {
      if (error.name === "AbortError" || id !== requestId) return;
      const notice = $("#notice"); notice.textContent = error.message; notice.classList.remove("hidden");
      for (const kind of ["lichess", "master"]) {
        const status = $(`#${kind}-status`); status.textContent = "Unavailable"; status.classList.add("error");
      }
    }
  }, delay);
}
async function load(positionChanged=false) {
  const id = ++requestId;
  clearTimeout(statsTimer);
  statsController?.abort();
  if (!positionChanged && data) {
    data = {...data, distributions: null};
    showStatisticsLoading();
    scheduleStatistics(id, 0);
    return;
  }
  engineRenderedKey = null;
  clearEngineForPosition();
  stateController?.abort();
  const moves = history.slice(0, cursor);
  const cacheKey = stateCacheKey(moves);
  const cached = positionStateCache.get(cacheKey);
  if (cached) {
    applyPositionState(cached, id);
    return;
  }
  $("#turn").textContent = "Updating position";
  const params = new URLSearchParams({
    moves: moves.join(",")
  });
  stateController = new AbortController();
  try {
    const response = await fetch("/api/state?" + params, {signal: stateController.signal});
    const payload = await readJsonResponse(response, "Board position");
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    if (id !== requestId) return;
    for (const state of payload.prefixes) {
      positionStateCache.set(stateCacheKey(state.position.uci_sequence), state);
    }
    applyPositionState(payload.current, id);
  } catch (error) {
    if (error.name === "AbortError" || id !== requestId) return;
    const notice = $("#notice"); notice.textContent = error.message; notice.classList.remove("hidden");
    $("#turn").textContent = "Position error";
  }
}
$("#back").onclick = () => { if (cursor) { cursor--; selected=null; load(true); } };
$("#forward").onclick = () => { if (cursor < history.length) { cursor++; selected=null; load(true); } };
$("#reset").onclick = () => { history=[]; cursor=0; selected=null; load(true); };
$("#ratings").onchange = () => load();
$("#speeds").onchange = () => load();
$("#frequency-threshold").onchange = () => { if (data) { renderMoves(); renderOpeningWiki(); } };
$("#openings-tab").onclick = () => {
  $("#openings-tab").classList.add("active");
  $("#explorer-tab").classList.remove("active");
  $("#opening-browser").classList.remove("hidden");
  $("#opening-guide").classList.add("hidden");
  renderOpeningWiki();
};
$("#explorer-tab").onclick = () => {
  $("#explorer-tab").classList.add("active");
  $("#openings-tab").classList.remove("active");
  $("#opening-browser").classList.add("hidden");
  $("#opening-guide").classList.add("hidden");
};
$("#engine-depth").onchange = () => scheduleEngine();
$("#engine-multipv").onchange = () => scheduleEngine();
$("#engine-toggle").onclick = () => {
  enginePaused = !enginePaused;
  $("#engine-toggle").textContent = enginePaused ? "Resume" : "Pause";
  if (enginePaused) cancelEngine("Paused"); else scheduleEngine();
};
$("#cancel-promotion").onclick = () => $("#promotion").close();
document.addEventListener("keydown", event => {
  if (event.key === "ArrowLeft") $("#back").click();
  if (event.key === "ArrowRight") $("#forward").click();
});
initOpenings();
load(true);
