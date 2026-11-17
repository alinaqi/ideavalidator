//! Request-body parsing and validation for the run API, kept pure so the boundary checks (reject an
//! empty pitch, an empty url) and the `pipeline.cli ingest` argv builder are unit-tested without a
//! server. The handler in [`crate::api`] turns a [`RunReq`] into a [`RunInput`] and never trusts the
//! raw JSON past this point.

use serde::Deserialize;

/// Raw run-submission body: either a one-line `pitch`, or a `url` (with an optional `angle`).
#[derive(Deserialize, Default)]
pub struct RunReq {
    #[serde(default)]
    pub pitch: Option<String>,
    #[serde(default)]
    pub url: Option<String>,
    #[serde(default)]
    pub angle: Option<String>,
}

/// A validated submission: exactly one of a pitch or a URL (with a possibly-empty angle).
#[derive(Debug, PartialEq)]
pub enum RunInput {
    Pitch(String),
    Url { url: String, angle: String },
}

fn non_empty(value: &Option<String>) -> Option<String> {
    value
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_string)
}

impl RunReq {
    /// Validate the body: a non-empty pitch wins, else a non-empty url; otherwise an error.
    pub fn validate(&self) -> Result<RunInput, String> {
        if let Some(pitch) = non_empty(&self.pitch) {
            return Ok(RunInput::Pitch(pitch));
        }
        match non_empty(&self.url) {
            Some(url) => Ok(RunInput::Url {
                url,
                angle: non_empty(&self.angle).unwrap_or_default(),
            }),
            None => Err("provide a non-empty pitch or url".to_string()),
        }
    }
}

/// Inputs for one `pipeline.cli ingest` invocation (a website URL, an optional angle, a target slug).
pub struct IngestArgs {
    pub url: String,
    pub angle: String,
    pub slug: String,
    pub ideas_dir: String,
}

/// Build the exact argv for `<python> -m pipeline.cli ingest ...` (pure; the spawn happens elsewhere).
pub fn ingest_argv(python: &str, a: &IngestArgs) -> Vec<String> {
    vec![
        python.to_string(),
        "-m".into(),
        "pipeline.cli".into(),
        "ingest".into(),
        "--url".into(),
        a.url.clone(),
        "--idea".into(),
        a.angle.clone(),
        "--slug".into(),
        a.slug.clone(),
        "--ideas-dir".into(),
        a.ideas_dir.clone(),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    fn req(pitch: Option<&str>, url: Option<&str>, angle: Option<&str>) -> RunReq {
        RunReq {
            pitch: pitch.map(str::to_string),
            url: url.map(str::to_string),
            angle: angle.map(str::to_string),
        }
    }

    #[test]
    fn pitch_is_trimmed_and_wins() {
        let got = req(Some("  an AI tutor  "), None, None).validate().unwrap();
        assert_eq!(got, RunInput::Pitch("an AI tutor".into()));
    }

    #[test]
    fn empty_pitch_is_rejected() {
        assert!(req(Some("   "), None, None).validate().is_err());
        assert!(req(Some(""), None, None).validate().is_err());
    }

    #[test]
    fn empty_url_is_rejected() {
        assert!(req(None, Some("  "), None).validate().is_err());
        assert!(req(None, None, None).validate().is_err());
    }

    #[test]
    fn url_form_keeps_url_and_optional_angle() {
        let got = req(None, Some("https://x.io"), Some("for nurses"))
            .validate()
            .unwrap();
        assert_eq!(
            got,
            RunInput::Url {
                url: "https://x.io".into(),
                angle: "for nurses".into(),
            }
        );
        let no_angle = req(None, Some("https://x.io"), None).validate().unwrap();
        assert_eq!(
            no_angle,
            RunInput::Url {
                url: "https://x.io".into(),
                angle: String::new(),
            }
        );
    }

    #[test]
    fn ingest_argv_is_the_exact_cli_shape() {
        let args = IngestArgs {
            url: "https://acme.io".into(),
            angle: "ai onboarding".into(),
            slug: "acme-ai".into(),
            ideas_dir: "ideas".into(),
        };
        assert_eq!(
            ingest_argv(".venv/bin/python", &args),
            vec![
                ".venv/bin/python",
                "-m",
                "pipeline.cli",
                "ingest",
                "--url",
                "https://acme.io",
                "--idea",
                "ai onboarding",
                "--slug",
                "acme-ai",
                "--ideas-dir",
                "ideas",
            ]
        );
    }
}
