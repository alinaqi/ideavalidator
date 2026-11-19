use super::*;
use serde_json::json;

#[test]
fn parses_the_last_line() {
    let out = "noise\n{\"status\":200,\"body\":{\"verdict\":\"ok\"}}\n\n";
    let r = parse_reply(out).unwrap();
    assert_eq!(r.status, 200);
    assert_eq!(r.body, json!({"verdict": "ok"}));
}

#[test]
fn rejects_empty_or_garbled_output() {
    assert!(parse_reply("").is_err());
    assert!(parse_reply("Traceback ...").is_err());
    assert!(parse_reply("{\"body\":{}}").is_err());
    assert!(parse_reply("{\"status\":99999,\"body\":{}}").is_err());
}

/// Real process plumbing with a stand-in `worker/req_check.py`: stdin in, key via env, one line out.
#[tokio::test]
async fn process_checker_round_trips_through_a_real_worker() {
    if std::process::Command::new("python3")
        .arg("-V")
        .output()
        .is_err()
    {
        return; // no interpreter on this machine; parse_reply above still covers the contract
    }
    let dir = std::env::temp_dir().join(format!("iv-reqcheck-{}", std::process::id()));
    std::fs::create_dir_all(dir.join("worker")).unwrap();
    std::fs::write(dir.join("worker/__init__.py"), "").unwrap();
    std::fs::write(
        dir.join("worker/req_check.py"),
        "import json, os, sys\nreq = json.load(sys.stdin)\n\
         print(json.dumps({'status': 200, 'body': {'n': len(req['requirements']), \
         'has_key': os.environ.get('PALGU_API_KEY') == 'tok'}}))\n",
    )
    .unwrap();
    let checker = ProcessChecker::new("python3".into(), dir.clone(), 2);
    let body = json!({"intent": "i", "requirements": [{"id": "R-1", "text": "t"}]});
    let reply = checker.check(body, "tok".into()).await.unwrap();
    assert_eq!(reply.status, 200);
    assert_eq!(reply.body, json!({"n": 1, "has_key": true}));
    let _ = std::fs::remove_dir_all(dir);
}
