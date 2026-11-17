//! Server-rendered dashboard (maud + HTMX + SSE): a shared themed [`layout`] and one module per page —
//! [`landing`] (`/`), [`app_page`] (`/app`) and [`run_page`] (`/app/runs/:id`). Handlers scope every
//! read to the session account and redirect, rather than 401, so the browser surface stays navigable.

pub mod app_page;
pub mod landing;
pub mod layout;
pub mod run_page;
