//! Stable per-Palgu-account identifier.

use sha2::{Digest, Sha256};

/// `sha256(email or "anon")` truncated to 16 hex chars.
///
/// Must byte-match the Python run store (`server/store.py::account_id`) so a user's existing hosted
/// runs stay keyed to the same account. The email is hashed as-is — do NOT normalize case or trim.
pub fn account_id(email: &str) -> String {
    let input = if email.is_empty() { "anon" } else { email };
    let digest = Sha256::digest(input.as_bytes());
    hex::encode(digest)[..16].to_string()
}

#[cfg(test)]
mod tests {
    use super::account_id;

    #[test]
    fn matches_python_vectors() {
        // Computed from server/store.py::account_id — cross-language contract.
        assert_eq!(account_id("a@b.com"), "fb98d44ad7501a95");
        assert_eq!(account_id(""), "5430eeed859cad61");
        assert_eq!(account_id("Ali@Palgu.ai"), "02886c3551e8b3fb");
    }

    #[test]
    fn case_is_significant() {
        assert_ne!(account_id("Ali@Palgu.ai"), account_id("ali@palgu.ai"));
    }
}
