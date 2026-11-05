const state = {
  mode: "idea",
  pending: false,
};

const modeConfig = {
  idea: {
    placeholder: "写下此刻的想法…",
    hint: "原文会保存到本地 raw 层，并自动更新索引。",
    endpoint: "/api/idea",
    userLabel: "保存想法",
  },
  link: {
    placeholder: "粘贴一个公开网页链接…",
    hint: "归藏会尝试提取网页正文；无法读取时不会编造内容。",
    endpoint: "/api/link",
    userLabel: "保存链接",
  },
  search: {
    placeholder: "输入关键词，或者你记得的一小段话…",
    hint: "会在标题、标签和正文中查找，支持完整片段和空格分隔关键词。",
    endpoint: "/api/search",
    userLabel: "查找知识",
  },
};

const conversation = document.querySelector("#conversation");
const composer = document.querySelector("#composer");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const hint = document.querySelector("#composer-hint");
const recentList = document.querySelector("#recent-list");
const knowledgeCount = document.querySelector("#knowledge-count");
const dialog = document.querySelector("#document-dialog");
let openDocumentPath = "";
const modelLabel = document.createElement("div");
modelLabel.className = "model-selector";
const providerInput = document.createElement("select");
providerInput.setAttribute("aria-label", "模型厂商");
const modelInput = document.createElement("select");
modelInput.setAttribute("aria-label", "模型");
const testButton = document.createElement("button");
testButton.type = "button";
testButton.textContent = "测试连接";
const modelStatus = document.createElement("span");
modelStatus.setAttribute("role", "status");
modelLabel.append(providerInput, modelInput, testButton, modelStatus);
composer.prepend(modelLabel);
testButton.disabled = true;
requestJson("/api/providers").then(({providers}) => {
  providers.forEach(p => providerInput.add(new Option(p.label, p.id)));
  providerInput.value = providers.some(p => p.id === localStorage.getItem("guizang-provider")) ? localStorage.getItem("guizang-provider") : "bailian";
  const updateModels = () => {
    const p = providers.find(p => p.id === providerInput.value);
    modelInput.replaceChildren();
    p.models.forEach(m => modelInput.add(new Option(m.label, m.id)));
    const saved = localStorage.getItem("guizang-model-" + p.id);
    if (p.models.some(m => m.id === saved)) modelInput.value = saved;
    localStorage.setItem("guizang-provider", p.id);
    modelStatus.textContent = p.configured ? "已配置密钥，待测试" : "尚未配置密钥";
    testButton.disabled = !p.configured;
  };
  providerInput.onchange = updateModels;
  modelInput.onchange = () => {
    localStorage.setItem("guizang-model-" + providerInput.value, modelInput.value);
    modelStatus.textContent = "模型已切换，请测试连接";
  };
  updateModels();
}).catch(error => { modelStatus.textContent = error.message; });
testButton.onclick = async () => {
  testButton.disabled = true;
  providerInput.disabled = modelInput.disabled = true;
  modelStatus.textContent = "正在连接…";
  try {
    const result = await requestJson("/api/model-test", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({provider: providerInput.value, model: modelInput.value}),
    });
    modelStatus.textContent = result.message;
  } catch (error) { modelStatus.textContent = error.message; }
  finally { testButton.disabled = false; providerInput.disabled = modelInput.disabled = false; }
};
const composerWrap = document.querySelector(".composer-wrap");
new ResizeObserver(() => {
  conversation.style.paddingBottom = `${composerWrap.getBoundingClientRect().height + 32}px`;
  document.documentElement.style.setProperty("--composer-height", `${composerWrap.getBoundingClientRect().height + 24}px`);
}).observe(composerWrap);

async function generateSummary(path, model, provider = providerInput.value) {
  addMessage("system", "原文已保存，正在生成摘要…");
  try {
    const result = await requestJson("/api/summarize", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, model, provider }),
    });
    addMessage("system", result.message);
    await refreshRecent();
  } catch (error) {
    addMessage("error", `原文仍已保存。${error.message}`);
    const retry = document.createElement("button");
    retry.textContent = "重试生成摘要";
    retry.onclick = async () => { retry.remove(); await generateSummary(path, modelInput.value.trim()); };
    conversation.appendChild(retry);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".mode-button").forEach((button) => {
    const active = button.dataset.mode === mode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-checked", active ? "true" : "false");
  });
  input.placeholder = modeConfig[mode].placeholder;
  hint.textContent = modeConfig[mode].hint;
  input.focus();
}

function addMessage(kind, text, results = []) {
  const message = document.createElement("section");
  message.className = `message ${kind}`;
  const cards = results.length
    ? `<div class="result-grid">${results.map((item) => `
        <button class="result-card" type="button" data-path="${escapeHtml(item.path)}">
          <div class="result-card-header">
            <span class="result-type">${escapeHtml(item.type_label)}</span>
            <strong>${escapeHtml(item.title)}</strong>
          </div>
          <p>${escapeHtml(item.snippet)}</p>
        </button>`).join("")}</div>`
    : "";
  message.innerHTML = `<div class="message-bubble">${escapeHtml(text)}${cards}</div>`;
  conversation.appendChild(message);
  message.scrollIntoView({ behavior: "smooth", block: "end" });
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "请求失败");
  }
  return payload;
}

async function refreshRecent() {
  try {
    const payload = await requestJson("/api/state");
    knowledgeCount.textContent = payload.count;
    if (!payload.recent.length) {
      recentList.innerHTML = '<div class="empty-small">还没有知识。先从一个想法开始。</div>';
      return;
    }
    recentList.innerHTML = payload.recent.map((item) => `
      <button class="recent-item" type="button" data-path="${escapeHtml(item.path)}">
        <strong>${escapeHtml(item.title)}</strong>
        <span>${escapeHtml(item.type_label)} · ${escapeHtml(item.updated_at)}</span>
      </button>`).join("");
  } catch (error) {
    recentList.innerHTML = `<div class="empty-small">${escapeHtml(error.message)}</div>`;
  }
}

async function openDocument(path) {
  try {
    const payload = await requestJson(`/api/document?path=${encodeURIComponent(path)}`);
    document.querySelector("#dialog-type").textContent = payload.type_label;
    document.querySelector("#dialog-title").textContent = payload.title;
    document.querySelector("#dialog-meta").textContent = `${payload.updated_at} · ${payload.path}`;
    document.querySelector("#dialog-content").textContent = payload.content;
    openDocumentPath = path;
    dialog.showModal();
  } catch (error) {
    addMessage("error", error.message);
  }
}

async function deleteOpenDocument() {
  if (!openDocumentPath) return;
  if (!window.confirm("确定删除这条知识吗？如果存在自动摘要，摘要也会一并删除。")) return;
  const button = document.querySelector("#dialog-delete");
  button.disabled = true;
  try {
    const result = await requestJson("/api/delete", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: openDocumentPath }),
    });
    dialog.close();
    addMessage("system", result.message);
    await refreshRecent();
    openDocumentPath = "";
    window.setTimeout(() => window.location.reload(), 350);
  } catch (error) {
    addMessage("error", error.message);
    button.disabled = false;
  }
}

async function submitMessage(event) {
  event.preventDefault();
  const content = input.value.trim();
  if (!content || state.pending) return;

  const mode = state.mode;
  addMessage("user", `${modeConfig[mode].userLabel}：${content}`);
  input.value = "";
  input.style.height = "auto";
  state.pending = true;
  sendButton.disabled = true;

  try {
    const payload = await requestJson(modeConfig[mode].endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    addMessage("system", payload.message, payload.results || []);
    if (mode !== "search") await generateSummary(payload.path, modelInput.value.trim());
    await refreshRecent();
  } catch (error) {
    addMessage("error", error.message);
    if (mode === "link" && /^https?:\/\//i.test(content)) showManualImport(content);
  } finally {
    state.pending = false;
    sendButton.disabled = false;
    input.focus();
  }
}

document.querySelectorAll(".mode-button").forEach((button) => {
  button.addEventListener("click", () => setMode(button.dataset.mode));
});

document.querySelectorAll("[data-quick-mode]").forEach((button) => {
  button.addEventListener("click", () => setMode(button.dataset.quickMode));
});

composer.addEventListener("submit", submitMessage);
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
});
input.addEventListener("keydown", (event) => {
  if (event.isComposing) return;
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    composer.requestSubmit();
  }
});

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-path]");
  if (target) openDocument(target.dataset.path);
});
document.querySelector("#dialog-close").addEventListener("click", () => dialog.close());
document.querySelector("#dialog-delete").addEventListener("click", deleteOpenDocument);
dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
});

setMode("idea");
refreshRecent();

function showManualImport(url) {
  const form = document.createElement("form");
  form.className = "manual-import";
  form.innerHTML = `<p>没有取得正文？在浏览器打开原文，复制后粘贴到这里。</p>
    <a target="_blank" rel="noopener noreferrer">打开原文 ↗</a>
    <label>文章标题<input name="title" required maxlength="80"></label>
    <label>文章正文<textarea name="body" required rows="6"></textarea></label>
    <button type="submit">保存正文</button><p role="status"></p>`;
  form.querySelector("a").href = url;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button");
    const status = form.querySelector('[role="status"]');
    button.disabled = true;
    status.textContent = "正在保存…";
    try {
      const payload = await requestJson("/api/link", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: url, title: form.elements.title.value, body: form.elements.body.value }),
      });
      status.textContent = payload.message;
      await generateSummary(payload.path, modelInput.value.trim());
      form.querySelectorAll("input, textarea").forEach((field) => { field.disabled = true; });
      await refreshRecent();
    } catch (error) {
      status.textContent = error.message;
      button.disabled = false;
    }
  });
  conversation.appendChild(form);
  form.scrollIntoView({ behavior: "smooth", block: "end" });
}
