//! Dependency-free UTC date formatting. The idea brief carries a `date:` frontmatter field; to match
//! `server/briefs.py` (which writes `date.today().isoformat()`) without pulling in a date crate, we
//! convert unix seconds to a civil `YYYY-MM-DD` date with Howard Hinnant's algorithm.

use std::time::{SystemTime, UNIX_EPOCH};

/// Today's UTC date as `YYYY-MM-DD`.
pub fn today_iso() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0);
    ymd_iso(secs)
}

/// Format a unix timestamp (seconds) as a UTC `YYYY-MM-DD` date.
pub fn ymd_iso(secs: i64) -> String {
    let (y, m, d) = civil_from_days(secs.div_euclid(86_400));
    format!("{y:04}-{m:02}-{d:02}")
}

/// Civil date from a count of days since the unix epoch (Howard Hinnant, public domain).
fn civil_from_days(days: i64) -> (i64, u32, u32) {
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let month = (if mp < 10 { mp + 3 } else { mp - 9 }) as u32;
    (yoe + era * 400 + i64::from(month <= 2), month, day)
}

#[cfg(test)]
mod tests {
    use super::ymd_iso;

    #[test]
    fn epoch_is_1970_01_01() {
        assert_eq!(ymd_iso(0), "1970-01-01");
    }

    #[test]
    fn known_timestamp_matches() {
        // 2023-11-14 22:13:20 UTC.
        assert_eq!(ymd_iso(1_700_000_000), "2023-11-14");
    }

    #[test]
    fn leap_day_is_handled() {
        // 2020-02-29 00:00:00 UTC == day 18321.
        assert_eq!(ymd_iso(18_321 * 86_400), "2020-02-29");
    }
}
