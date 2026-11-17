//! Shared page shell for the server-rendered dashboard: a themed, responsive HTML document with inline
//! CSS and the HTMX script (pinned, from a CDN). Every page calls [`page`] so the chrome, theme tokens
//! and typography stay consistent across landing, dashboard and run views.

use maud::{html, Markup, PreEscaped, DOCTYPE};

const HTMX_SRC: &str = "https://cdnjs.cloudflare.com/ajax/libs/htmx.org/2.0.4/htmx.min.js";

const APP_CSS: &str = ":root{--bg:#f7f7fb;--fg:#17172a;--muted:#5b5b74;--card:#fff;--line:#e4e4ef;\
--brand:#4f46e5;--go:#16885f;--kill:#c0392b;--pivot:#b8860b}\
@media(prefers-color-scheme:dark){:root{--bg:#0f0f17;--fg:#e9e9f2;--muted:#9a9ab4;--card:#1a1a28;\
--line:#2a2a3c;--brand:#8b84ff}}\
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);\
font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}\
.wrap{max-width:52rem;margin:0 auto;padding:1.5rem 1rem}\
header.top{display:flex;justify-content:space-between;align-items:center;gap:1rem;margin-bottom:1.5rem}\
a{color:var(--brand)}h1{font-size:1.6rem;margin:.2rem 0}\
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:1.25rem;\
margin-bottom:1rem}\
label{display:block;font-weight:600;margin:.6rem 0 .25rem}\
input,textarea,select{width:100%;padding:.6rem;border:1px solid var(--line);border-radius:8px;\
background:transparent;color:inherit;font:inherit}textarea{min-height:5rem;resize:vertical}\
button{background:var(--brand);color:#fff;border:0;border-radius:8px;padding:.6rem 1.1rem;\
font:inherit;font-weight:600;cursor:pointer;margin-top:.8rem}button:disabled{opacity:.5}\
.row{display:flex;justify-content:space-between;align-items:center;gap:.75rem;padding:.6rem 0;\
border-top:1px solid var(--line)}.row:first-child{border-top:0}\
.badge{font-size:.78rem;font-weight:700;padding:.15rem .55rem;border-radius:999px;\
border:1px solid var(--line);text-transform:uppercase;letter-spacing:.03em}\
.muted{color:var(--muted)}.go{color:var(--go)}.kill{color:var(--kill)}.pivot{color:var(--pivot)}\
ol.stages{list-style:none;padding:0;margin:0}ol.stages li{display:flex;justify-content:space-between;\
padding:.5rem 0;border-top:1px solid var(--line)}ol.stages li.done{color:var(--go)}\
.code{font-family:ui-monospace,Menlo,monospace;font-size:1.4rem;letter-spacing:.2em}";

/// Wrap `body` in the full themed document (`title` is suffixed with the product name).
pub fn page(title: &str, body: Markup) -> Markup {
    html! {
        (DOCTYPE)
        html lang="en" {
            head {
                meta charset="utf-8";
                meta name="viewport" content="width=device-width,initial-scale=1";
                title { (title) " · ideavalidator" }
                style { (PreEscaped(APP_CSS)) }
                script src=(HTMX_SRC) defer {}
            }
            body { div.wrap { (body) } }
        }
    }
}
