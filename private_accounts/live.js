// All requests stay on this page's private origin. Only read-only regions are replaced.
(() => {
  let busy = false;
  let lastResearch = 0;
  const managerLink = document.querySelector('.desk-tabs a[aria-current="page"][href$="/desk/manager"]');
  const portfolioLink = document.querySelector('.desk-tabs a[href$="/portfolio"]');
  // Older Mac listeners serve this asset from disk while their quote collectors stay active.
  const olderHome = managerLink && portfolioLink && !document.querySelector(".manager-jumps");
  function showPositions(region, first = false) {
    const positions = region?.querySelector("#live-positions");
    const balances = region?.querySelector(".value-grid");
    if (positions && balances) {
      balances.after(positions);
      if (first) positions.open = true;
    }
  }
  function restoreHome() {
    const live = document.getElementById("live-values");
    const title = document.querySelector(".desk-title");
    if (!live || !title) return;
    const wrapper = live.closest(".desk-balances");
    title.after(live);
    if (wrapper) wrapper.remove();
    showPositions(live, true);
    const heading = Array.from(document.querySelectorAll(".chat-card h2"))
      .find(h => h.textContent.trim() === "분야별 최신 결과");
    const desks = document.createElement("section");
    desks.id = "manager-desks";
    live.after(desks);
    if (heading) {
      const links = [];
      for (let el = heading.nextElementSibling; el?.matches('a.desk-link[href*="/desk/"]'); el = el.nextElementSibling) links.push(el);
      const cards = document.createElement("div");
      cards.className = "analysts";
      for (const a of links) { a.classList.add("card"); cards.append(a); }
      desks.append(heading, cards);
    }
    const positionLink = document.createElement("a");
    positionLink.className = "desk-link";
    positionLink.href = portfolioLink.href + "#holdings";
    positionLink.textContent = "보유 종목별 담당과 근거";
    live.after(positionLink);
  }
  async function restoreCategories() {
    const response = await fetch(portfolioLink.href, {mode:"same-origin", cache:"no-store",
      referrerPolicy:"no-referrer", signal:AbortSignal.timeout(12000)});
    if (!response.ok) throw Error();
    const page = new DOMParser().parseFromString(await response.text(), "text/html");
    const categories = page.getElementById("analysts");
    if (!categories) return;
    const current = document.getElementById("analysts");
    if (current) {
      if (!current.contains(document.activeElement)) current.replaceWith(categories);
    } else document.getElementById("manager-desks")?.after(categories);
  }
  function received() {
    const status = document.querySelector("[data-poll-status]");
    if (status) {
      const clock = new Intl.DateTimeFormat("ko-KR", {timeZone: "Asia/Seoul",
        dateStyle: "medium", timeStyle: "medium"});
      status.textContent = "브라우저 화면 수신 " + clock.format(new Date()) + " KST";
    }
  }
  received();
  async function update() {
    if (document.hidden || busy) return;
    busy = true;
    try {
      const refreshResearch = managerLink && Date.now() - lastResearch >= 60000;
      const headers = {"X-Live-Sections": "1"};
      if (refreshResearch) headers["X-Research-Sections"] = "1";
      const response = await fetch(location.href, {cache: "no-store", mode: "same-origin",
        referrerPolicy: "no-referrer", headers, signal: AbortSignal.timeout(12000)});
      if (!response.ok) throw Error();
      const incoming = new DOMParser().parseFromString(await response.text(), "text/html");
      const targets = document.querySelectorAll("[data-watch][id]");
      let replacedValues = false;
      for (const old of targets) {
        const next = incoming.getElementById(old.id);
        if (!next || old.contains(document.activeElement) && document.activeElement.matches("input,select,textarea")) continue;
        if (old.dataset.revision && old.dataset.revision === next.dataset.revision) continue;
        if (olderHome && old.id === "live-values") showPositions(next);
        const scroll = Array.from(old.querySelectorAll(".comparison,.panel"), el => [el.scrollLeft, el.scrollTop]);
        const details = Array.from(old.querySelectorAll("details"));
        const focus = details.findIndex(d => d.querySelector(":scope > summary") === document.activeElement);
        next.querySelectorAll("details").forEach((d, i) => { if (details[i]) d.open = details[i].open; });
        old.replaceWith(next);
        if (next.id === "live-values") replacedValues = true;
        next.querySelectorAll(".comparison,.panel").forEach((el, i) => {
          if (scroll[i]) [el.scrollLeft, el.scrollTop] = scroll[i];
        });
        if (focus >= 0) next.querySelectorAll("details")[focus]?.querySelector("summary")?.focus({preventScroll:true});
      }
      if (replacedValues) received();
      if (refreshResearch) {
        lastResearch = Date.now();
        if (olderHome) await restoreCategories();
      }
    } catch {
      const status = document.querySelector("[data-poll-status]");
      if (status) status.textContent = "화면 갱신 연결 실패 · 마지막 표시값 유지";
    } finally { busy = false; }
  }
  document.addEventListener("change", event => {
    if (event.target.matches(".history-select select")) event.target.form.requestSubmit();
  });
  if (olderHome) { restoreHome(); update(); }
  const compactView = managerLink || /\/accounts\/?$/.test(location.pathname);
  setInterval(update, compactView ? 5000 : 15000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) update(); });
})();
