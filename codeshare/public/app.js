const $ = (id) => document.getElementById(id);
const STORAGE_KEY = "codeshare.local.v1";
const form = $("snippet-form");
const codeInput = $("code");
const languageInput = $("language");
const titleInput = $("title");
const saveButton = $("save-btn");
let latestEditToken = "";
let toastTimer;

function toast(message) {
  const el = $("toast"); el.textContent = message; el.classList.add("show");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove("show"), 2600);
}
function getLibrary() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); } catch { return []; }
}
function setLibrary(items) { localStorage.setItem(STORAGE_KEY, JSON.stringify(items)); }
function safeDate(value) {
  if (!value) return "Just now";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Just now" : date.toLocaleString();
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function updateEditorMeta() {
  $("char-count").textContent = codeInput.value.length.toLocaleString();
  const ext = ({python:"py",javascript:"js",typescript:"ts",java:"java",sql:"sql",html:"html",css:"css",json:"json",bash:"sh",go:"go",rust:"rs",c:"c",cpp:"cpp",csharp:"cs",ruby:"rb",php:"php",yaml:"yml",powershell:"ps1"})[languageInput.value] || "txt";
  $("editor-label").textContent = `main.${ext}`;
}
function renderLibrary() {
  const query = ($("search").value || "").toLowerCase().trim();
  const items = getLibrary().filter(x => `${x.title} ${x.language} ${x.code}`.toLowerCase().includes(query));
  $("snippet-total").textContent = getLibrary().length;
  const list = $("snippet-list");
  if (!items.length) {
    list.innerHTML = `<div class="empty-state"><div class="empty-icon">{ }</div><h3>${query ? "No matching snippets" : "Your library is waiting"}</h3><p>${query ? "Try a different search term." : "Save your first snippet and it will appear here on this device."}</p></div>`;
    return;
  }
  list.innerHTML = items.map(item => `<article class="snippet-card">
    <div class="snippet-card-head"><div><h3>${escapeHtml(item.title)}</h3><span class="language-badge">${escapeHtml(item.language)}</span></div><time>${escapeHtml(safeDate(item.created_at))}</time></div>
    <pre class="snippet-preview">${escapeHtml(item.code.slice(0,260))}${item.code.length>260?"…":""}</pre>
    <div class="snippet-card-actions">
      <button class="mini-button" data-action="open" data-id="${item.id}">Open ↗</button>
      <button class="mini-button" data-action="copy" data-id="${item.id}">Copy code</button>
      <button class="mini-button" data-action="edit" data-id="${item.id}">Edit</button>
      <button class="mini-button danger" data-action="delete" data-id="${item.id}">Delete</button>
    </div></article>`).join("");
}
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); }
  catch {
    const input = document.createElement("textarea"); input.value = text; document.body.appendChild(input);
    input.select(); document.execCommand("copy"); input.remove();
  }
}
function showResult(item, token) {
  latestEditToken = token || "";
  $("share-result").classList.remove("hidden");
  const url = `${location.origin}/s/${item.id}`;
  $("share-url").value = url; $("open-share").href = url;
  $("edit-key-note").textContent = token ? "Edit key saved in this browser. Copy it somewhere safe before clearing browser data." : "This snippet was opened from your local library.";
  $("copy-edit-key").classList.toggle("hidden", !token);
  $("share-result").scrollIntoView({behavior:"smooth",block:"center"});
}
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {title:titleInput.value.trim(), language:languageInput.value, code:codeInput.value};
  if (!payload.code.trim()) { $("form-message").textContent = "Paste some code before saving."; return; }
  if (payload.code.length > 100000) { $("form-message").textContent = "Code must be 100,000 characters or fewer."; return; }
  saveButton.disabled = true; saveButton.innerHTML = "Saving…"; $("form-message").textContent = "";
  try {
    const response = await fetch("/api/snippets", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Could not save snippet.");
    const library = getLibrary();
    library.unshift({...result, edit_token:result.edit_token});
    setLibrary(library);
    showResult(result, result.edit_token);
    renderLibrary();
    toast("Snippet saved. Your share link is ready.");
  } catch (error) {
    $("form-message").textContent = `${error.message} Check your database configuration and try again.`;
  } finally {
    saveButton.disabled = false; saveButton.innerHTML = '<span>Save & generate link</span><span class="arrow">↗</span>';
  }
});
$("copy-link").addEventListener("click", async () => { await copyText($("share-url").value); toast("Share link copied."); });
$("copy-edit-key").addEventListener("click", async () => { if(latestEditToken) { await copyText(latestEditToken); toast("Edit key copied. Keep it private."); }});
$("search").addEventListener("input", renderLibrary);
languageInput.addEventListener("change", updateEditorMeta);
codeInput.addEventListener("input", updateEditorMeta);
$("snippet-list").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]"); if (!button) return;
  const item = getLibrary().find(x => x.id === button.dataset.id); if (!item) return;
  const action = button.dataset.action;
  if (action === "open") location.href = `/s/${item.id}`;
  if (action === "copy") { await copyText(item.code); toast("Code copied."); }
  if (action === "edit") {
    titleInput.value = item.title; languageInput.value = item.language; codeInput.value = item.code; updateEditorMeta();
    form.dataset.editId = item.id; form.dataset.editToken = item.edit_token || "";
    saveButton.innerHTML = '<span>Save changes</span><span class="arrow">↗</span>';
    $("form-message").textContent = "Editing local snippet. Use the edit key to save changes to the shared version.";
    if (!item.edit_token) toast("Edit key is unavailable in this browser.");
    $("create").scrollIntoView({behavior:"smooth"});
  }
  if (action === "delete") {
    if (!confirm(`Delete "${item.title}" from the shared database? This cannot be undone.`)) return;
    try {
      const response = await fetch(`/api/snippets/${item.id}`, {method:"DELETE",headers:{"Authorization":`Bearer ${item.edit_token || ""}`}});
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Delete failed");
      setLibrary(getLibrary().filter(x => x.id !== item.id)); renderLibrary(); toast("Snippet deleted.");
    } catch (error) { toast(error.message); }
  }
});
// Save edits if a local item is selected for editing; otherwise create a new snippet.
const originalSubmit = form.onsubmit;
form.addEventListener("submit", async (event) => {
  const id = form.dataset.editId;
  if (!id) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  const item = getLibrary().find(x => x.id === id);
  const token = form.dataset.editToken || item?.edit_token || "";
  if (!token) { toast("No edit key available. You can still create a new snippet."); return; }
  saveButton.disabled = true;
  try {
    const response = await fetch(`/api/snippets/${id}`, {method:"PUT",headers:{"Content-Type":"application/json","Authorization":`Bearer ${token}`},body:JSON.stringify({title:titleInput.value.trim(),language:languageInput.value,code:codeInput.value})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Update failed");
    setLibrary(getLibrary().map(x => x.id === id ? {...result, edit_token:token} : x));
    delete form.dataset.editId; delete form.dataset.editToken;
    saveButton.innerHTML = '<span>Save & generate link</span><span class="arrow">↗</span>';
    showResult(result, token); renderLibrary(); toast("Snippet updated.");
  } catch(error) { $("form-message").textContent = error.message; }
  finally { saveButton.disabled = false; }
}, true);
updateEditorMeta(); renderLibrary();
