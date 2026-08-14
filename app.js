const state = {
  cases: [],
  current: null,
  steps: [],
};

const $ = (id) => document.getElementById(id);

async function boot() {
  const res = await fetch("/api/cases");
  const data = await res.json();
  state.cases = data.cases || [];
  $("case-count").textContent = `${state.cases.length} cases`;
  const pick = $("case-pick");
  pick.innerHTML = state.cases
    .map((item) => `<option value="${item.id}">${item.cart.manufacturer} ${item.cart.model} — ${item.title}</option>`)
    .join("");
  $("trainee").value = localStorage.getItem("smi-trainer-name") || "";
}

function renderJob(item) {
  state.current = item;
  state.steps = [];
  $("job").classList.remove("hidden");
  $("work").classList.remove("hidden");
  $("report").classList.add("hidden");
  $("job-setting").textContent = item.setting;
  $("job-title").textContent = item.title;
  $("job-ticket").textContent = item.ticket;
  const cart = item.cart;
  $("job-cart").innerHTML = [
    ["Type", `${cart.category} · ${cart.manufacturer} ${cart.model}`],
    ["Year / volts", `${cart.year} · ${cart.voltage}`],
    ["Top", cart.top],
    ["Notes", cart.notes],
  ]
    .map(([k, v]) => `<div><strong>${k}</strong><br>${v}</div>`)
    .join("");
  renderSteps();
  $("step").focus();
}

function renderSteps() {
  $("step-list").innerHTML = state.steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("");
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function addStep() {
  const text = $("step").value.trim();
  if (!text) return;
  state.steps.push(text);
  $("step").value = "";
  renderSteps();
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

async function grade() {
  if (!state.current || !state.steps.length) return;
  const res = await fetch("/api/grade", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      trainee: $("trainee").value.trim(),
      case_id: state.current.id,
      steps: state.steps,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    $("report").classList.remove("hidden");
    $("report").textContent = data.detail || "Could not grade";
    return;
  }
  const cls = data.result === "pass" ? "pass" : data.result === "almost" ? "almost" : "fail";
  $("report").classList.remove("hidden");
  $("report").innerHTML = `
    <p class="score ${cls}">${data.score}</p>
    <p>${escapeHtml(data.feedback)}</p>
    <p><strong>What it actually was</strong><br>${escapeHtml(data.cause)}</p>
    ${listBlock("You hit", data.hits)}
    ${listBlock("You missed", data.misses)}
    ${listBlock("Don't do this", data.fouls, "label")}
  `;
}

function listBlock(title, items, key = "label") {
  if (!items || !items.length) return "";
  return `<p><strong>${title}</strong></p><ul class="list">${items
    .map((item) => `<li>${escapeHtml(item[key] || item.label)}</li>`)
    .join("")}</ul>`;
}

$("start-btn").addEventListener("click", () => startCase($("case-pick").value));
$("random-btn").addEventListener("click", () => {
  const pick = state.cases[Math.floor(Math.random() * state.cases.length)];
  if (pick) {
    $("case-pick").value = pick.id;
    startCase(pick.id);
  }
});
$("add-btn").addEventListener("click", addStep);
$("undo-btn").addEventListener("click", () => {
  state.steps.pop();
  renderSteps();
});
$("grade-btn").addEventListener("click", grade);
$("step").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    addStep();
  }
});

boot();
