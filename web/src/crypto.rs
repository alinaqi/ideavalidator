//! AES-256-GCM encryption of a Palgu token at rest. The key comes from `TOKEN_ENC_KEY`
//! (32 bytes, base64 or hex). The blob is `base64(nonce || ciphertext)`. The key and the
//! plaintext token are never logged.

use aes_gcm::aead::{Aead, AeadCore, KeyInit, OsRng};
use aes_gcm::{Aes256Gcm, Nonce};
use base64::engine::general_purpose::STANDARD;
use base64::Engine;

const NONCE_LEN: usize = 12;

pub struct Cipher {
    inner: Aes256Gcm,
}

impl Cipher {
    /// Build from the raw `TOKEN_ENC_KEY` value, which must decode to exactly 32 bytes.
    pub fn from_env_key(raw: &str) -> Result<Self, String> {
        let key = parse_key(raw)?;
        Ok(Cipher {
            inner: Aes256Gcm::new((&key).into()),
        })
    }

    /// Returns `base64(nonce || ciphertext)`. A fresh random nonce is used every call.
    pub fn encrypt(&self, plaintext: &str) -> Result<String, String> {
        let nonce = Aes256Gcm::generate_nonce(&mut OsRng);
        let ct = self
            .inner
            .encrypt(&nonce, plaintext.as_bytes())
            .map_err(|_| "encrypt failed".to_string())?;
        let mut out = nonce.to_vec();
        out.extend_from_slice(&ct);
        Ok(STANDARD.encode(out))
    }

    /// Reverse of [`encrypt`]; errors on a bad key, tampering, or a malformed blob.
    pub fn decrypt(&self, blob: &str) -> Result<String, String> {
        let data = STANDARD
            .decode(blob)
            .map_err(|_| "bad base64".to_string())?;
        if data.len() <= NONCE_LEN {
            return Err("blob too short".into());
        }
        let (nonce, ct) = data.split_at(NONCE_LEN);
        let pt = self
            .inner
            .decrypt(Nonce::from_slice(nonce), ct)
            .map_err(|_| "decrypt failed".to_string())?;
        String::from_utf8(pt).map_err(|_| "bad utf8".into())
    }
}

/// Decode a 32-byte key from base64 or hex, preferring whichever yields exactly 32 bytes.
fn parse_key(raw: &str) -> Result<[u8; 32], String> {
    let raw = raw.trim();
    [hex::decode(raw).ok(), STANDARD.decode(raw).ok()]
        .into_iter()
        .flatten()
        .find_map(|b| <[u8; 32]>::try_from(b).ok())
        .ok_or_else(|| "TOKEN_ENC_KEY must decode (base64 or hex) to 32 bytes".to_string())
}

#[cfg(test)]
mod tests {
    use super::Cipher;

    const KEY_B64: &str = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
    const KEY_HEX: &str = "1111111111111111111111111111111111111111111111111111111111111111";

    #[test]
    fn round_trips_base64_and_hex_keys() {
        for raw in [KEY_B64, KEY_HEX] {
            let c = Cipher::from_env_key(raw).unwrap();
            let blob = c.encrypt("palgu-secret-token").unwrap();
            assert_eq!(c.decrypt(&blob).unwrap(), "palgu-secret-token");
        }
    }

    #[test]
    fn nonce_is_random_so_blobs_differ() {
        let c = Cipher::from_env_key(KEY_B64).unwrap();
        assert_ne!(c.encrypt("x").unwrap(), c.encrypt("x").unwrap());
    }

    #[test]
    fn decrypt_with_wrong_key_fails() {
        let blob = Cipher::from_env_key(KEY_B64)
            .unwrap()
            .encrypt("tok")
            .unwrap();
        assert!(Cipher::from_env_key(KEY_HEX)
            .unwrap()
            .decrypt(&blob)
            .is_err());
    }

    #[test]
    fn tampered_ciphertext_fails() {
        let c = Cipher::from_env_key(KEY_B64).unwrap();
        let mut blob = c.encrypt("tok").unwrap();
        blob.insert(0, if blob.starts_with('A') { 'B' } else { 'A' });
        assert!(c.decrypt(&blob).is_err());
    }

    #[test]
    fn wrong_key_length_is_rejected() {
        assert!(Cipher::from_env_key("deadbeef").is_err());
        assert!(Cipher::from_env_key("not-valid-anything").is_err());
    }
}
