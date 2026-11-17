//! A fan-out hub for live run progress, keyed by `run_id`. Each run gets a `tokio::broadcast` channel;
//! the orchestrator [`publish`](SseHub::publish)es every [`Event`] and HTTP handlers (P3) call
//! [`subscribe`](SseHub::subscribe) to stream Server-Sent Events. Publishing with no subscribers is a
//! no-op, and a subscriber created after earlier events simply starts from the next one — never blocks.

use std::collections::HashMap;
use std::sync::Mutex;

use tokio::sync::broadcast::{self, Receiver, Sender};

use crate::events::Event;

const CAPACITY: usize = 256;

#[derive(Default)]
pub struct SseHub {
    channels: Mutex<HashMap<String, Sender<Event>>>,
}

impl SseHub {
    pub fn new() -> Self {
        Self::default()
    }

    /// Subscribe to a run's event stream (creating the channel if needed).
    pub fn subscribe(&self, run_id: &str) -> Receiver<Event> {
        self.sender(run_id).subscribe()
    }

    /// Broadcast one event to a run's subscribers; a no-op when there are none.
    pub fn publish(&self, run_id: &str, event: Event) {
        let _ = self.sender(run_id).send(event);
    }

    fn sender(&self, run_id: &str) -> Sender<Event> {
        self.channels
            .lock()
            .unwrap()
            .entry(run_id.to_string())
            .or_insert_with(|| broadcast::channel(CAPACITY).0)
            .clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn done() -> Event {
        Event::Done
    }

    #[tokio::test]
    async fn subscriber_receives_published_event() {
        let hub = SseHub::new();
        let mut rx = hub.subscribe("r1");
        hub.publish("r1", done());
        assert_eq!(rx.recv().await.unwrap(), Event::Done);
    }

    #[tokio::test]
    async fn publish_without_subscribers_is_ok() {
        let hub = SseHub::new();
        hub.publish("r1", done()); // must not panic or error out
    }

    #[tokio::test]
    async fn late_subscriber_gets_next_event_not_a_deadlock() {
        let hub = SseHub::new();
        hub.publish("r1", done()); // dropped: no receivers yet
        let mut late = hub.subscribe("r1");
        hub.publish("r1", Event::Cancelled);
        assert_eq!(late.recv().await.unwrap(), Event::Cancelled);
    }

    #[tokio::test]
    async fn separate_runs_do_not_cross_talk() {
        let hub = SseHub::new();
        let mut a = hub.subscribe("a");
        let mut b = hub.subscribe("b");
        hub.publish("a", done());
        assert_eq!(a.recv().await.unwrap(), Event::Done);
        assert!(b.try_recv().is_err());
    }
}
