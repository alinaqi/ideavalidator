//! Opaque session tokens and the `Set-Cookie` / `Cookie` plumbing. The token is random and never
//! derived from the account, so it reveals nothing; the cookie is HttpOnly + Secure + SameSite=Lax.

use rand::RngCore;

pub const SESSION_COOKIE: &str = "iv_session";
/// Fourteen days, in seconds.
pub const SESSION_MAX_AGE: i64 = 60 * 60 * 24 * 14;

/// A fresh 256-bit opaque token, hex-encoded.
pub fn new_token() -> String {
    let mut bytes = [0u8; 32];
    rand::rngs::OsRng.fill_bytes(&mut bytes);
    hex::encode(bytes)
}

/// Build the `Set-Cookie` value for a session token with the given lifetime.
pub fn build_cookie(token: &str, max_age: i64) -> String {
    format!("{SESSION_COOKIE}={token}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age={max_age}")
}

/// The `Set-Cookie` value that expires the session immediately (logout).
pub fn clear_cookie() -> String {
    build_cookie("", 0)
}

/// Pull the session token out of a `Cookie` request header, if present.
pub fn parse_cookie(header: &str) -> Option<String> {
    let prefix = format!("{SESSION_COOKIE}=");
    header
        .split(';')
        .map(str::trim)
        .find_map(|part| part.strip_prefix(&prefix))
        .filter(|v| !v.is_empty())
        .map(str::to_string)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tokens_are_random_and_long() {
        let (a, b) = (new_token(), new_token());
        assert_ne!(a, b);
        assert_eq!(a.len(), 64);
    }

    #[test]
    fn cookie_has_security_attributes() {
        let c = build_cookie("abc", SESSION_MAX_AGE);
        assert!(c.contains("iv_session=abc"));
        assert!(c.contains("HttpOnly"));
        assert!(c.contains("Secure"));
        assert!(c.contains("SameSite=Lax"));
        assert!(c.contains("Path=/"));
        assert!(c.contains("Max-Age=1209600"));
    }

    #[test]
    fn parse_round_trips_among_other_cookies() {
        let header = "theme=dark; iv_session=tok123; other=1";
        assert_eq!(parse_cookie(header), Some("tok123".to_string()));
    }

    #[test]
    fn parse_rejects_missing_or_empty() {
        assert_eq!(parse_cookie("theme=dark"), None);
        assert_eq!(parse_cookie("iv_session=; x=1"), None);
        assert_eq!(parse_cookie(""), None);
    }

    #[test]
    fn clear_cookie_expires_now() {
        assert!(clear_cookie().contains("Max-Age=0"));
    }
}
