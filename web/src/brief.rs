//! Port of `server/briefs.py`: turn a one-line pitch into a minimal idea brief the pipeline can run.
//! `slug` normalises the pitch for a filesystem key; `brief_md` renders the template with the pitch under
//! "## One-sentence pitch"; `write_brief` persists it so the spawned worker can load it.

use std::path::{Path, PathBuf};

use crate::datefmt::today_iso;

fn is_kept(c: char) -> bool {
    c.is_ascii_lowercase() || c.is_ascii_digit() || c.is_whitespace() || c == '-'
}

/// Normalise a pitch to a slug, matching `server/briefs.py::_slug`: lowercase, drop characters outside
/// `[a-z0-9\s-]`, join words with `-`, cut to 40 chars, trim stray dashes; empty falls back to `idea`.
pub fn slug(pitch: &str) -> String {
    let cleaned: String = pitch
        .to_lowercase()
        .chars()
        .filter(|c| is_kept(*c))
        .collect();
    let joined = cleaned.split_whitespace().collect::<Vec<_>>().join("-");
    let capped: String = joined.chars().take(40).collect();
    let trimmed = capped.trim_matches('-');
    if trimmed.is_empty() {
        "idea".to_string()
    } else {
        trimmed.to_string()
    }
}

/// Render the brief markdown, mirroring `server/briefs.py::_brief_md`.
pub fn brief_md(slug: &str, pitch: &str) -> String {
    let title: String = pitch.chars().take(60).collect();
    format!(
        "---\nslug: {slug}\ntitle: {title}\ndate: {date}\nstatus: intake\n---\n\n\
         # Idea brief\n\n## One-sentence pitch\n{pitch}\n",
        date = today_iso(),
    )
}

/// Write `<run_dir>/<slug>.md` for the engine to load; returns the slug and the brief's path.
pub fn write_brief(run_dir: &Path, pitch: &str) -> Result<(String, PathBuf), String> {
    let slug = slug(pitch);
    let path = run_dir.join(format!("{slug}.md"));
    std::fs::create_dir_all(run_dir).map_err(|e| e.to_string())?;
    std::fs::write(&path, brief_md(&slug, pitch)).map_err(|e| e.to_string())?;
    Ok((slug, path))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slug_normalises_like_python() {
        assert_eq!(slug("Hello, World!"), "hello-world");
        assert_eq!(slug("A/B & C"), "ab-c");
        assert_eq!(slug("   "), "idea");
        assert_eq!(slug(""), "idea");
    }

    #[test]
    fn slug_caps_at_forty_chars_then_trims() {
        let long = "word ".repeat(20);
        let s = slug(&long);
        assert!(s.len() <= 40, "slug too long: {s}");
        assert!(!s.ends_with('-'));
    }

    #[test]
    fn brief_md_holds_pitch_under_heading() {
        let md = brief_md("demo", "An AI tutor for nurses");
        assert!(md.contains("## One-sentence pitch\nAn AI tutor for nurses\n"));
        assert!(md.contains("slug: demo"));
        assert!(md.contains("status: intake"));
    }

    #[test]
    fn write_brief_creates_the_file() {
        let dir = std::env::temp_dir().join(format!("iv-brief-{}", std::process::id()));
        let (slug, path) = write_brief(&dir, "Test pitch here").unwrap();
        assert_eq!(slug, "test-pitch-here");
        let body = std::fs::read_to_string(&path).unwrap();
        assert!(body.contains("Test pitch here"));
        let _ = std::fs::remove_dir_all(&dir);
    }
}
