//! `GET /` — the landing page. Signed-in callers are redirected to the dashboard; everyone else sees a
//! "Sign in with Palgu" panel that drives the device-code flow (`/auth/start` then polling `/auth/poll`)
//! with a small inline script, showing the user code and verification link while it waits for approval.

use axum::extract::State;
use axum::http::HeaderMap;
use axum::response::{IntoResponse, Redirect, Response};
use maud::{html, Markup, PreEscaped};

use crate::extract::account_from_headers;
use crate::state::AppState;

use super::layout::page;

const SIGNIN_JS: &str = "const btn=document.getElementById('signin'),out=document.getElementById('device');\
let timer;btn.addEventListener('click',async()=>{btn.disabled=true;\
const d=await(await fetch('/auth/start',{method:'POST'})).json();\
out.innerHTML=`<p>Open <a href=\"${d.verification_uri}\" target=\"_blank\" rel=\"noopener\">${d.verification_uri}</a> and enter this code:</p>\
<p class=\"code\">${d.user_code}</p><p class=\"muted\">Waiting for approval…</p>`;\
timer=setInterval(()=>poll(d.poll_token),4000);});\
async function poll(t){const d=await(await fetch('/auth/poll',{method:'POST',\
headers:{'content-type':'application/json'},body:JSON.stringify({poll_token:t})})).json();\
if(d.status==='signed_in'){clearInterval(timer);location.href='/app';}\
else if(d.status==='stopped'){clearInterval(timer);out.innerHTML='<p class=\"kill\">Sign-in stopped: '+d.reason+'</p>';}}";

fn panel() -> Markup {
    html! {
        header.top { h1 { "ideavalidator" } }
        div.card {
            p { "Validate a business idea end to end — problem, market, ICP, willingness to pay, "
                "day-one economics and a GO / PIVOT / KILL memo — on your own Palgu key." }
            button id="signin" { "Sign in with Palgu" }
            div id="device" {}
        }
        script { (PreEscaped(SIGNIN_JS)) }
    }
}

/// Render the landing page, or redirect a signed-in visitor straight to the dashboard.
pub async fn landing(State(st): State<AppState>, headers: HeaderMap) -> Response {
    if account_from_headers(&headers, &st).await.is_some() {
        return Redirect::to("/app").into_response();
    }
    page("Sign in", panel()).into_response()
}

#[cfg(test)]
mod tests {
    use super::panel;

    #[test]
    fn panel_has_the_signin_button_and_device_slot() {
        let html = panel().into_string();
        assert!(html.contains("id=\"signin\""));
        assert!(html.contains("id=\"device\""));
        assert!(html.contains("Sign in with Palgu"));
    }
}
