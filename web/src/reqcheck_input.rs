//! Contract-v1 request validation for the requirements check, mirroring `pipeline/reqcheck.py`
//! (`validate_request`). Both sides run the shared fixtures in `tests/fixtures/requirements_check/`.
//! Rejecting here answers 422 at once, without spawning the worker.

use std::collections::HashSet;

use serde_json::Value;

const MAX_INTENT: usize = 4000;
const MAX_REQS: usize = 200;
const MAX_TEXT: usize = 4000;

fn non_empty(v: &Value, max: usize) -> bool {
    v.as_str()
        .map(|s| !s.trim().is_empty() && s.chars().count() <= max)
        .unwrap_or(false)
}

fn id_of(r: &Value) -> Option<String> {
    match &r["id"] {
        Value::String(s) if !s.trim().is_empty() => Some(s.clone()),
        Value::Number(n) => Some(n.to_string()),
        _ => None,
    }
}

fn check_requirements(reqs: &Value) -> Result<(), String> {
    let list = reqs
        .as_array()
        .filter(|l| (1..=MAX_REQS).contains(&l.len()))
        .ok_or(format!(
            "requirements must be a list of 1..{MAX_REQS} items"
        ))?;
    let mut seen = HashSet::new();
    for (i, r) in list.iter().enumerate() {
        let id = id_of(r).filter(|_| non_empty(&r["text"], MAX_TEXT));
        let id = id.ok_or(format!(
            "requirements[{i}] needs a non-empty id and text (<= {MAX_TEXT} chars)"
        ))?;
        if !seen.insert(id) {
            return Err("requirement ids must be unique".into());
        }
    }
    Ok(())
}

/// `Ok(())` when the body follows contract v1, else the first reason it does not.
pub fn validate(body: &Value) -> Result<(), String> {
    if !body.is_object() {
        return Err("body must be a JSON object".into());
    }
    if !non_empty(&body["intent"], MAX_INTENT) {
        return Err(format!(
            "intent must be a non-empty string of at most {MAX_INTENT} chars"
        ));
    }
    check_requirements(&body["requirements"])?;
    if !(body["context"].is_object() || body["context"].is_null()) {
        return Err("context must be an object".into());
    }
    match &body["depth"] {
        Value::Null => Ok(()),
        Value::String(d) if d == "quick" => Ok(()),
        _ => Err("depth must be 'quick' (the only depth contract v1 defines)".into()),
    }
}

/// Count-only description for logs: never the intent or requirement text.
pub fn log_counts(body: &Value) -> String {
    let n = body["requirements"].as_array().map_or(0, |l| l.len());
    let new_product = body["context"]["existing_app"] == Value::Bool(false);
    format!("requirements={n} new_product={new_product}")
}
