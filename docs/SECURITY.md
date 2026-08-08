# MANAR QC — Security & Compliance Architecture

## OWASP ASVS 5.0 Level 2 Hardening

### V2 Authentication
- Password hashing using Argon2id (`Argon2PasswordHasher`). Minimum password length 12 chars.
- Tester shift authentication with 6-digit PIN hashed via Argon2id.
- IP-based rate limiting on `/accounts/login/` (10 requests/minute).

### V3 Session Management
- 12-hour idle timeout (`SESSION_COOKIE_AGE = 43200`, `SESSION_SAVE_EVERY_REQUEST = True`).
- Strict cookie flags: `HttpOnly`, `SameSite=Lax`, `Secure` in production.

### V4 Access Control & Tenant Isolation
- Hard multi-tenant isolation enforced via `TenantModel` base class and mandatory `.for_vendor(vendor)` queryset filtering.
- Automated two-tenant cross-boundary leakage suite tested in `core/tests.py`.

### V6 Cryptography & Data Integrity
- Offline Ed25519 signing for all `.mpk` station packs (`pynacl`). Signing keys stored off-server.
- Station measurement records appended to sha256 hash chains (`hash = sha256(prev_hash + body)`).

### Sovereignty Invariant
- Garment photos and raw measurements remain on factory station PCs by default.
- Only opt-in signed summary aggregates and hash chains are uploaded to the portal via `/sync/upload/`.
