const state = {
  cases: [],
  current: null,
  already: [],
  solved: false,
  lastHint: "",
};

const $ = (id) => document.getElementById(id);

async function boot() {
  const res = await fetch("/api/cases");
  const data = await res.json();
  state.cases = data.cases || [];
  $("case-count").textContent = `${state.cases.length} cases`;
  $("case-pick").innerHTML = state.cases
    .map((item) => `<option value="${item.id}">${item.cart.manufacturer} ${item.cart.model} — ${item.title}</option>`)
    .join("");
  $("trainee").value = localStorage.getItem("smi-trainer-name") || "";
}

function addLine(who, text, extra) {
  const row = document.createElement("div");
  row.className = `line ${who}${extra ? " " + extra : ""}`;
  row.innerHTML = `<span>${who === "you" ? "You" : "Cart"}</span><p>${escapeHtml(text)}</p>`;
  $("log").appendChild(row);
  $("log").scrollTop = $("log").scrollHeight;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderJob(item) {
  state.current = item;
  state.already = [];
  state.solved = false;
  state.lastHint = "";
  $("job").classList.remove("hidden");
  $("work").classList.remove("hidden");
  $("next-btn").classList.add("hidden");
  $("add-btn").disabled = false;
  $("step").disabled = false;
  $("log").innerHTML = "";
  $("job-setting").textContent = item.setting;
  $("job-title").textContent = item.title;
  $("job-ticket").textContent = item.ticket;
  const cart = item.cart;
  $("job-cart").innerHTML = [
    ["Type", `${cart.category} · ${cart.manufacturer} ${cart.model}`],
    ["Year / fuel", `${cart.year} · ${cart.fuel || "Gasoline"}`],
    ["Engine", cart.engine || "Gas"],
    ["Top", cart.top],
  ]
    .map(([k, v]) => `<div><strong>${k}</strong><br>${v}</div>`)
    .join("");
  addLine("cart", "What do you want to check?");
  $("step").focus();
}

async function startCase(id) {
  const name = $("trainee").value.trim();
  if (!name) {
    $("trainee").focus();
    return;
  }
  localStorage.setItem("smi-trainer-name", name);
  const res = await fetch(`/api/cases/${id}`);
  if (!res.ok) return;
  renderJob(await res.json());
}

async function checkIt() {
  if (!state.current || state.solved) return;
  const text = $("step").value.trim();
  if (!text) return;
  $("step").value = "";
  addLine("you", text);
  const res = await fetch("/api/act", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      case_id: state.current.id,
      step: text,
      already: state.already,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    addLine("cart", data.detail || "Couldn't read that.");
    return;
  }
  state.already = data.already || state.already;
  state.lastHint = data.hint || state.lastHint;
  addLine("cart", data.reply, data.kind);
  if (data.solved) {
    state.solved = true;
    addLine("cart", data.cause, "pass");
    $("add-btn").disabled = true;
    $("step").disabled = true;
    $("next-btn").classList.remove("hidden");
    fetch("/api/grade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        trainee: $("trainee").value.trim() || "tech",
        case_id: state.current.id,
        steps: [text],
      }),
    }).catch(() => {});
  }
  $("step").focus();
}

$("start-btn").addEventListener("click", () => startCase($("case-pick").value));
$("random-btn").addEventListener("click", () => {
  const pick = state.cases[Math.floor(Math.random() * state.cases.length)];
  if (pick) {
    $("case-pick").value = pick.id;
    startCase(pick.id);
  }
});
$("add-btn").addEventListener("click", checkIt);
$("hint-btn").addEventListener("click", () => {
  addLine("cart", state.lastHint || "Check the cheap stuff first. Gas, spark, oil, belt.");
});
$("next-btn").addEventListener("click", () => {
  const ids = state.cases.map((item) => item.id);
  const here = ids.indexOf(state.current?.id);
  const next = state.cases[(here + 1) % state.cases.length];
  startCase(next.id);
});
$("step").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    checkIt();
  }
});

boot();
