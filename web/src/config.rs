//! Runtime configuration, read from the process environment with safe local defaults.

use std::net::SocketAddr;

#[derive(Debug, Clone)]
pub struct Config {
    pub addr: SocketAddr,
    pub database_url: String,
    pub store_dir: String,
    pub palgu_origin: String,
    pub token_enc_key: String,
    pub python_bin: String,
    pub max_concurrent_runs: usize,
    /// Hard deadline for one requirements check; past it the route answers 503 (contract: <= 45 s).
    pub req_check_timeout_ms: u64,
    pub max_concurrent_checks: usize,
}

fn parse_cap(raw: Option<String>) -> usize {
    parse_positive(raw, 3)
}

fn parse_positive<T: std::str::FromStr + PartialOrd + Default>(raw: Option<String>, dflt: T) -> T {
    raw.and_then(|v| v.parse().ok())
        .filter(|n| *n > T::default())
        .unwrap_or(dflt)
}

impl Config {
    /// Build from the real process environment.
    pub fn from_env() -> Self {
        Self::from(|key| std::env::var(key).ok())
    }

    /// Build from an injected getter (used by tests; keeps `from_env` a one-liner).
    pub fn from(get: impl Fn(&str) -> Option<String>) -> Self {
        let port: u16 = get("PORT").and_then(|p| p.parse().ok()).unwrap_or(8000);
        Config {
            addr: SocketAddr::from(([0, 0, 0, 0], port)),
            database_url: get("DATABASE_URL").unwrap_or_default(),
            store_dir: get("IV_STORE").unwrap_or_else(|| "server_runs".into()),
            palgu_origin: get("PALGU_ORIGIN").unwrap_or_else(|| "https://api.palgu.ai".into()),
            token_enc_key: get("TOKEN_ENC_KEY").unwrap_or_default(),
            python_bin: get("PYTHON_BIN").unwrap_or_else(|| ".venv/bin/python".into()),
            max_concurrent_runs: parse_cap(get("MAX_CONCURRENT_RUNS")),
            req_check_timeout_ms: parse_positive(get("REQ_CHECK_TIMEOUT_MS"), 45_000),
            max_concurrent_checks: parse_positive(get("MAX_CONCURRENT_CHECKS"), 8),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::Config;
    use std::collections::HashMap;

    #[test]
    fn uses_defaults_when_unset() {
        let c = Config::from(|_| None);
        assert_eq!(c.addr.port(), 8000);
        assert_eq!(c.store_dir, "server_runs");
        assert_eq!(c.palgu_origin, "https://api.palgu.ai");
        assert_eq!(c.python_bin, ".venv/bin/python");
        assert_eq!(c.max_concurrent_runs, 3);
        assert_eq!(c.req_check_timeout_ms, 45_000);
        assert_eq!(c.max_concurrent_checks, 8);
    }

    #[test]
    fn req_check_limits_parse_and_guard_zero() {
        let c = Config::from(|k| (k == "REQ_CHECK_TIMEOUT_MS").then(|| "1500".to_string()));
        assert_eq!(c.req_check_timeout_ms, 1500);
        let z = Config::from(|k| (k == "MAX_CONCURRENT_CHECKS").then(|| "0".to_string()));
        assert_eq!(z.max_concurrent_checks, 8);
    }

    #[test]
    fn concurrency_cap_parses_and_guards_zero() {
        let c = Config::from(|k| (k == "MAX_CONCURRENT_RUNS").then(|| "5".to_string()));
        assert_eq!(c.max_concurrent_runs, 5);
        let z = Config::from(|k| (k == "MAX_CONCURRENT_RUNS").then(|| "0".to_string()));
        assert_eq!(z.max_concurrent_runs, 3);
    }

    #[test]
    fn env_overrides_win() {
        let env: HashMap<&str, &str> = [("PORT", "9000"), ("IV_STORE", "/data")].into();
        let c = Config::from(|k| env.get(k).map(|s| s.to_string()));
        assert_eq!(c.addr.port(), 9000);
        assert_eq!(c.store_dir, "/data");
    }
}
