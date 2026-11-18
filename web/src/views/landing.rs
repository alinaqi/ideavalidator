//! `GET /` — the landing page. Signed-in callers are redirected to the dashboard; everyone else sees a
//! "Sign in with Palgu" panel. One click starts the device flow (`/auth/start`) and opens Palgu's
//! sign-in page with the code pre-filled (`verification_uri_complete`): the visitor logs in there with
//! their email + one-time code, and this page polls `/auth/poll` and signs itself in automatically —
//! no code to copy. A visible fallback link covers blocked pop-ups.

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
const url=d.verification_uri_complete||d.verification_uri;\
const w=window.open(url,'_blank','noopener');\
out.innerHTML=`<p>We opened <strong>Palgu</strong> in a new tab — sign in with your email and the one-time code, then come back here.</p>\
<p class=\"muted\">This page signs you in automatically once you approve.</p>\
<p><a href=\"${url}\" target=\"_blank\" rel=\"noopener\">Open the Palgu sign-in page</a>${w?'':' — your browser blocked the pop-up, click to open'}</p>\
<p class=\"muted\">Approval code: <span class=\"code\">${d.user_code}</span></p>`;\
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
            p.muted { "Sign in with your Palgu account — email and a one-time code. New to Palgu? "
                "The same page lets you sign up." }
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

    #[test]
    fn panel_opens_palgu_with_the_prefilled_code() {
        let html = panel().into_string();
        assert!(html.contains("verification_uri_complete"));
        assert!(html.contains("window.open(url"));
    }
}
