//! Shared page shell for the server-rendered dashboard: a themed, responsive HTML document with inline
//! CSS and the HTMX script (pinned, from a CDN). Every page calls [`page`] so the chrome, theme tokens
//! and typography stay consistent across landing, dashboard and run views.

use maud::{html, Markup, PreEscaped, DOCTYPE};

const HTMX_SRC: &str = "https://cdnjs.cloudflare.com/ajax/libs/htmx.org/2.0.4/htmx.min.js";

// Glassmorphic theme: an ambient gradient backdrop with translucent, backdrop-blurred panels. Class and
// token names are unchanged, so the views and their tests are untouched. Theme-aware (light/dark).
const APP_CSS: &str = r#":root{--fg:#15152b;--muted:#565677;--brand:#5b4ff0;--go:#0f9d63;--kill:#d14343;
--pivot:#bd8a1e;--bg:#e8ebfb;--glass:rgba(255,255,255,.55);--glass-2:rgba(255,255,255,.72);
--line:rgba(120,120,165,.28);--hair:rgba(120,120,165,.18);--shadow:0 12px 40px -14px rgba(40,30,90,.35)}
@media(prefers-color-scheme:dark){:root{--fg:#ececf7;--muted:#a6a6c6;--brand:#9a92ff;--go:#3ad29a;
--kill:#ff6b6b;--pivot:#e3b94e;--bg:#0b0b15;--glass:rgba(255,255,255,.06);--glass-2:rgba(255,255,255,.1);
--line:rgba(255,255,255,.14);--hair:rgba(255,255,255,.08);--shadow:0 22px 54px -22px rgba(0,0,0,.72)}}
*{box-sizing:border-box}html{min-height:100%}
body{margin:0;min-height:100vh;color:var(--fg);background:var(--bg);background-attachment:fixed;
background-image:radial-gradient(44rem 44rem at 10% -10%,rgba(99,91,255,.45),transparent 60%),
radial-gradient(38rem 38rem at 96% 6%,rgba(20,190,170,.4),transparent 55%),
radial-gradient(42rem 42rem at 72% 108%,rgba(236,72,153,.34),transparent 60%);
font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
@media(prefers-color-scheme:dark){body{background-image:
radial-gradient(44rem 44rem at 10% -10%,rgba(99,91,255,.5),transparent 60%),
radial-gradient(38rem 38rem at 96% 6%,rgba(18,150,175,.44),transparent 55%),
radial-gradient(42rem 42rem at 72% 108%,rgba(190,60,160,.42),transparent 60%)}}
.wrap{max-width:52rem;margin:0 auto;padding:1.9rem 1rem}
header.top{display:flex;justify-content:space-between;align-items:center;gap:1rem;margin-bottom:1.6rem}
a{color:var(--brand);text-decoration:none}a:hover{text-decoration:underline}
h1{font-size:1.65rem;margin:.2rem 0;letter-spacing:-.01em}
.card{background:var(--glass);border:1px solid var(--line);border-radius:18px;padding:1.45rem;
margin-bottom:1.1rem;box-shadow:var(--shadow);-webkit-backdrop-filter:blur(20px) saturate(165%);
backdrop-filter:blur(20px) saturate(165%)}
label{display:block;font-weight:600;margin:.7rem 0 .3rem}
input,textarea,select{width:100%;padding:.65rem .7rem;border:1px solid var(--line);border-radius:12px;
background:var(--glass-2);color:inherit;font:inherit;-webkit-backdrop-filter:blur(6px);
backdrop-filter:blur(6px)}input::placeholder,textarea::placeholder{color:var(--muted)}
textarea{min-height:5rem;resize:vertical}
input:focus,textarea:focus,select:focus{outline:none;border-color:var(--brand);
box-shadow:0 0 0 3px color-mix(in srgb,var(--brand) 32%,transparent)}
button{background:linear-gradient(135deg,var(--brand),color-mix(in srgb,var(--brand) 62%,#22d3ee));
color:#fff;border:0;border-radius:12px;padding:.65rem 1.25rem;font:inherit;font-weight:600;
cursor:pointer;margin-top:.9rem;box-shadow:0 10px 24px -10px color-mix(in srgb,var(--brand) 70%,transparent)}
button:hover{filter:brightness(1.06)}button:disabled{opacity:.5}
.row{display:flex;justify-content:space-between;align-items:center;gap:.75rem;padding:.7rem 0;
border-top:1px solid var(--hair)}.row:first-child{border-top:0}a.row:hover{text-decoration:none;opacity:.82}
.badge{font-size:.72rem;font-weight:700;padding:.2rem .6rem;border-radius:999px;border:1px solid var(--line);
background:var(--glass-2);text-transform:uppercase;letter-spacing:.04em}
.muted{color:var(--muted)}.go{color:var(--go)}.kill{color:var(--kill)}.pivot{color:var(--pivot)}
ol.stages{list-style:none;padding:0;margin:.3rem 0 0}ol.stages li{display:flex;
justify-content:space-between;padding:.58rem 0;border-top:1px solid var(--hair)}
ol.stages li:first-child{border-top:0}ol.stages li.done{color:var(--go)}
.code{font-family:ui-monospace,Menlo,monospace;font-size:1.5rem;letter-spacing:.2em}"#;

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
