const $ = id => document.getElementById(id);
let snippet = null, toastTimer;
function toast(message) {
  const el = $("toast"); el.textContent = message; el.classList.add("show");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove("show"), 2400);
}
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); }
  catch { const t=document.createElement("textarea");t.value=text;document.body.appendChild(t);t.select();document.execCommand("copy");t.remove(); }
}
function languageClass(language) {
  const aliases = {csharp:"csharp",cpp:"cpp",plaintext:"plaintext",powershell:"powershell"};
  return aliases[language] || language || "plaintext";
}
async function loadSnippet() {
  const match = location.pathname.match(/^\/s\/([a-z0-9]{12})\/?$/);
  if (!match) return showNotFound();
  try {
    const response = await fetch(`/api/snippets/${match[1]}`);
    if (!response.ok) return showNotFound();
    snippet = await response.json();
    $("loading").classList.add("hidden");
    $("snippet-content").classList.remove("hidden");
    document.title = `${snippet.title} — CodeShare`;
    $("snippet-title").textContent = snippet.title;
    $("snippet-language").textContent = snippet.language;
    $("snippet-date").textContent = `Created ${new Date(snippet.created_at).toLocaleDateString()}`;
    $("snippet-views").textContent = `${snippet.views} views`;
    const code = $("snippet-code"); code.textContent = snippet.code; code.className = `language-${languageClass(snippet.language)}`;
    $("filename").textContent = `snippet.${({python:"py",javascript:"js",typescript:"ts",java:"java",sql:"sql",html:"html",css:"css",json:"json",bash:"sh",go:"go",rust:"rs",c:"c",cpp:"cpp",csharp:"cs",ruby:"rb",php:"php",yaml:"yml",powershell:"ps1"})[snippet.language] || "txt"}`;
    $("line-count").textContent = `${snippet.code.split("\n").length} lines`;
    if (window.hljs) window.hljs.highlightElement(code);
  } catch { showNotFound(); }
}
function showNotFound() { $("loading").classList.add("hidden"); $("not-found").classList.remove("hidden"); }
$("copy-code").addEventListener("click", async () => { if(snippet) { await copyText(snippet.code); toast("Code copied to clipboard."); } });
$("copy-share").addEventListener("click", async () => { await copyText(location.href); toast("Share link copied."); });
loadSnippet();
