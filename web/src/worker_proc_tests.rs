//! Unit tests for [`crate::worker_proc`]: the pump forwards a real child's stdout lines (hermetic `sh`,
//! no network), and the fake spawner yields scripted lines for the orchestration tests.

use super::*;

#[tokio::test]
async fn pump_forwards_child_stdout_lines() {
    let mut cmd = Command::new("sh");
    cmd.arg("-c")
        .arg("printf 'a\\nb\\n'")
        .stdout(Stdio::piped());
    let mut child = cmd.spawn().unwrap();
    let stdout = child.stdout.take().unwrap();
    let (tx, mut rx) = mpsc::channel(8);
    let pump = Pump {
        child,
        tx,
        cancel: CancelToken::new(),
    };
    tokio::spawn(pump.run(stdout));
    assert_eq!(rx.recv().await, Some("a".to_string()));
    assert_eq!(rx.recv().await, Some("b".to_string()));
    assert_eq!(rx.recv().await, None);
}

#[tokio::test]
async fn fake_spawner_yields_scripted_lines() {
    let spawner = FakeSpawner {
        lines: vec!["one".into(), "two".into()],
        wait_cancel: false,
    };
    let mut worker = spawner.spawn_for_test(CancelToken::new()).await;
    assert_eq!(worker.lines.recv().await, Some("one".to_string()));
    assert_eq!(worker.lines.recv().await, Some("two".to_string()));
    assert_eq!(worker.lines.recv().await, None);
}
