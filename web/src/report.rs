//! Render the engine's decision memo (`<run>/<slug>/decision.md`) to a standalone HTML page with inline
//! CSS, using `pulldown-cmark`. Kept pure (`&str` in, `String` out) so P4's `get_report` and the web run
//! page share one renderer, and so the markdown->html mapping is unit-tested without the filesystem.

use pulldown_cmark::{html, Options, Parser};

const REPORT_CSS: &str = "body{max-width:46rem;margin:2rem auto;padding:0 1rem;\
font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a2e;\
background:#fff}h1,h2,h3{line-height:1.25;margin-top:1.6em}code{background:#f0f0f4;\
padding:.1em .3em;border-radius:4px}pre{background:#f6f6fb;padding:1rem;overflow:auto;\
border-radius:8px}table{border-collapse:collapse}th,td{border:1px solid #ddd;padding:.4rem .6rem}\
@media(prefers-color-scheme:dark){body{color:#e8e8f0;background:#14141f}code,pre{background:#20202e}\
th,td{border-color:#333}}";

/// Convert CommonMark (with tables/strikethrough) to an HTML fragment.
pub fn markdown_to_html(md: &str) -> String {
    let mut options = Options::empty();
    options.insert(Options::ENABLE_TABLES);
    options.insert(Options::ENABLE_STRIKETHROUGH);
    let parser = Parser::new_ext(md, options);
    let mut out = String::new();
    html::push_html(&mut out, parser);
    out
}

/// Wrap the rendered memo in a full, themed HTML document with inline CSS.
pub fn report_page(md: &str) -> String {
    format!(
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">\
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\
<title>Decision memo</title><style>{REPORT_CSS}</style></head><body>{body}</body></html>",
        body = markdown_to_html(md),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn headings_and_emphasis_become_html() {
        let html = markdown_to_html("# Decision: GO\n\nStrong **market** fit.");
        assert!(html.contains("<h1>Decision: GO</h1>"));
        assert!(html.contains("<strong>market</strong>"));
    }

    #[test]
    fn tables_render_with_the_tables_option() {
        let md = "| Stage | Verdict |\n|---|---|\n| market | GO |\n";
        let html = markdown_to_html(md);
        assert!(html.contains("<table>"));
        assert!(html.contains("<td>market</td>"));
    }

    #[test]
    fn report_page_is_a_full_themed_document() {
        let page = report_page("## Summary\n\nShip it.");
        assert!(page.starts_with("<!doctype html>"));
        assert!(page.contains("<h2>Summary</h2>"));
        assert!(page.contains("prefers-color-scheme:dark"));
        assert!(page.contains("<title>Decision memo</title>"));
    }
}
