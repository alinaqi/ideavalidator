//! Parse one line of the worker's NDJSON progress stream into a typed [`Event`]. The exact line shapes
//! come from `worker/run_job.py` (see `tests/test_worker_run_job.py`). Blank, malformed, or event-less
//! lines yield `None` so the caller skips them; a recognised JSON object with an unknown `event` maps to
//! [`Event::Unknown`]. Parsing never panics.

use serde_json::Value;

/// One decoded progress event from the worker.
#[derive(Clone, Debug, PartialEq)]
pub enum Event {
    Stage {
        stage: String,
        verdict: Option<String>,
        score: Option<f64>,
    },
    Done,
    Cancelled,
    Error {
        error: String,
    },
    Unknown,
}

fn as_opt_string(v: &Value, key: &str) -> Option<String> {
    v.get(key).and_then(Value::as_str).map(str::to_string)
}

fn stage_event(v: &Value) -> Event {
    Event::Stage {
        stage: as_opt_string(v, "stage").unwrap_or_default(),
        verdict: as_opt_string(v, "verdict"),
        score: v.get("score").and_then(Value::as_f64),
    }
}

fn classify(v: &Value, kind: &str) -> Event {
    match kind {
        "stage" => stage_event(v),
        "done" => Event::Done,
        "cancelled" => Event::Cancelled,
        "error" => Event::Error {
            error: as_opt_string(v, "error").unwrap_or_default(),
        },
        _ => Event::Unknown,
    }
}

/// Decode one NDJSON line. `None` for blank/malformed/event-less lines; otherwise a typed event.
pub fn parse_line(line: &str) -> Option<Event> {
    let value: Value = serde_json::from_str(line.trim()).ok()?;
    let kind = value.get("event").and_then(Value::as_str)?;
    Some(classify(&value, kind))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_the_exact_stage_line() {
        let line = r#"{"event":"stage","stage":"market","verdict":"GO","score":4.2}"#;
        assert_eq!(
            parse_line(line),
            Some(Event::Stage {
                stage: "market".into(),
                verdict: Some("GO".into()),
                score: Some(4.2),
            })
        );
    }

    #[test]
    fn parses_done_cancelled_and_error() {
        assert_eq!(parse_line(r#"{"event":"done"}"#), Some(Event::Done));
        assert_eq!(
            parse_line(r#"{"event":"cancelled"}"#),
            Some(Event::Cancelled)
        );
        assert_eq!(
            parse_line(r#"{"event":"error","error":"boom"}"#),
            Some(Event::Error {
                error: "boom".into()
            })
        );
    }

    #[test]
    fn stage_tolerates_null_verdict_and_score() {
        let line = r#"{"event":"stage","stage":"frame","verdict":null,"score":null}"#;
        assert_eq!(
            parse_line(line),
            Some(Event::Stage {
                stage: "frame".into(),
                verdict: None,
                score: None,
            })
        );
    }

    #[test]
    fn unknown_event_maps_to_unknown() {
        assert_eq!(parse_line(r#"{"event":"heartbeat"}"#), Some(Event::Unknown));
    }

    #[test]
    fn junk_and_blank_and_eventless_are_none() {
        assert_eq!(parse_line(""), None);
        assert_eq!(parse_line("   "), None);
        assert_eq!(parse_line("not json at all"), None);
        assert_eq!(parse_line("{}"), None);
        assert_eq!(parse_line(r#"{"foo":1}"#), None);
    }
}
