# KisanBackend — Architecture & Conventions Reference

> Use this file as a guide when refactoring, adding features, or onboarding.
> Every pattern here was established during the initial architecture review of this codebase.

---

## Project Layout

```
KisanBackend/
└── kisan_backend/
    ├── api/
    │   └── v1/
    │       ├── dependencies/   # FastAPI Depends factories (auth, db, redis)
    │       └── endpoints/      # Thin HTTP routers — request/response shaping ONLY
    ├── core/
    │   ├── constants.py        # All magic numbers and config values
    │   ├── messages.py         # All user-facing response strings (single source of truth)
    │   ├── responses.py        # Shared SuccessResponse / ApiResponse helpers
    │   └── ws_manager.py       # WebSocket connection registry
    ├── db/
    │   ├── session.py          # SQLAlchemy async engine + migrations
    │   └── redis.py            # Redis connection factory
    ├── middleware/
    │   └── logging.py          # Request/response structured logging
    ├── models/                 # SQLAlchemy ORM models (single file per entity)
    ├── repositories/           # Data access layer — DB queries only, no business logic
    ├── schemas/                # Pydantic request/response schemas
    └── services/               # Business logic — orchestrates repos, raises exceptions
```

---

## Architecture Principles

### 1. Clean Architecture / SRP

Each layer has exactly one responsibility:

| Layer | Responsibility | Must NOT |
|---|---|---|
| `endpoints/` | Parse request, call service, shape HTTP response | Contain business logic or DB queries |
| `services/` | Orchestrate business rules, call repositories | Know about HTTP, headers, or request objects |
| `repositories/` | Execute DB queries | Contain business logic |
| `dependencies/` | Construct services, parse shared request metadata | Contain business logic |

> **Rule:** If a function needs the `Request` object, it belongs in `endpoints/` or `dependencies/`, never in `services/`.

### 2. Dependency Injection via `auth_deps.py`

All service construction lives in `kisan_backend/api/v1/dependencies/auth_deps.py`.

```python
# Convenience alias — use everywhere in endpoint signatures
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
```

Helper functions also live here:
- `get_device_meta(request)` — extracts `X-Device-*` headers into a `DeviceMetadata` schema
- `is_browser_request(request)` — returns `True` if request is from a browser (vs native mobile app)

### 3. Centralized Constants — `core/constants.py`

**Never hardcode** magic numbers in service or endpoint files. All config lives in named classes:

```python
class OTPConfig:     # OTP lengths, backoff map, Redis key prefixes
class SessionConfig: # Handover timeout, Redis key prefix, token TTLs
class TokenConfig:   # Proactive refresh thresholds, reuse windows
class DeviceHeaders: # HTTP header name strings (X-Device-Id, X-Device-Browser, etc.)
```

### 4. Centralized Messages — `core/messages.py`

**Never hardcode** user-facing strings in services or endpoints. All strings live in `ResponseMessages`:

```python
ResponseMessages.OTP_SENT          # success strings
ResponseMessages.ACCESS_DENIED_ADMIN_ONLY   # access control
ResponseMessages.ACCESS_DENIED_BROWSER_FARMERS  # channel-specific denial
ResponseMessages.SESSION_CONFLICT   # session management
```

When adding a new message: add to `messages.py` first, then reference it everywhere.

---

## Access Control Policy

### Channel-Aware Role Guard (in `endpoints/auth.py`)

```
Browser client  (X-Device-Browser != "N/A") → ADMIN only
Native app      (X-Device-Browser == "N/A") → ADMIN + FARMER
```

Detection helper: `is_browser_request(request)` in `auth_deps.py`.

> **Rule:** Role-based access control lives in the **endpoint layer** only — the service layer rejects unknown users (no account), not wrong roles.

### Why this separation matters

The service layer (`auth_service.py`) has no access to the HTTP request. It cannot know which channel the request came from. Therefore:
- `auth_service.verify_otp()` → rejects **unknown phone numbers** only
- `auth.py` endpoint → enforces **role + channel** policy after the service returns

---

## Session Management

### Session Conflict Flow (Admin)

1. OTP verified → `auth_service.verify_otp()` returns user
2. Endpoint checks for active sessions on **other** devices
3. If conflict found → returns `session_conflict: True` with metadata (no tokens issued)
4. Client shows alert dialog
5. Client sends `force: true` on confirmation → triggers handover flow

### Force Login Handover Flow

1. `session_revoked` WebSocket event broadcast to all of the user's existing connections
2. All DB sessions deactivated + Redis keys purged
3. Endpoint waits up to `SessionConfig.HANDOVER_TIMEOUT_SECONDS` for old client to disconnect
4. New session + tokens created for incoming device

---

## WebSocket Transport

Endpoint: `GET /api/v1/auth/ws/{token}?meta={base64_device_info}`

- `meta` param is base64-encoded JSON of device headers (sent by client on connect)
- All frames must include a signed `Authorization: Bearer <token>` header inside the envelope
- Heartbeat: client sends `{ event: "heartbeat", type: "ping" }` every 30–60s
- Auto token refresh: backend pushes fresh tokens every 60s via `{ event: "system", type: "token" }`

### System Events (server → client)

| Event type | Meaning |
|---|---|
| `session_revoked` | Another device force-logged in; client must logout |
| `token` | Fresh token pair pushed proactively |
| `pong` | Heartbeat acknowledgement |
| `error` | Malformed frame or server error |

---

## Device Metadata Headers

Defined in `DeviceHeaders` constants class. Sent by all clients on every request:

| Header | Flutter value | Browser value |
|---|---|---|
| `X-Device-Id` | Device UUID | Browser fingerprint / `unknown` |
| `X-Device-Brand` | `realme`, `samsung`, etc. | `unknown` |
| `X-Device-Model` | Model string | `unknown` |
| `X-Device-OS` | `android` / `ios` | `unknown` |
| `X-Device-OS-Version` | OS version string | `unknown` |
| `X-App-Version` | App semver | App semver |
| `X-Device-Browser` | `N/A` | `Chrome` / `Firefox` / etc. |

> `X-Device-Browser: N/A` is the **sentinel** that identifies native mobile app requests.

---

## Response Shape

Always use the helpers in `core/responses.py`:

```python
return SuccessResponse(message=ResponseMessages.OTP_SENT, data={...})
return ApiResponse(success=False, message=ResponseMessages.ACCESS_DENIED_ADMIN_ONLY, status_code=403)
```

Never build raw dicts as responses in endpoint files.

---

## Key Refactoring Rules

1. **No hardcoded strings** — always `ResponseMessages.XYZ`
2. **No hardcoded numbers** — always `OTPConfig.XYZ`, `SessionConfig.XYZ`, etc.
3. **No business logic in endpoints** — move to services
4. **No HTTP context in services** — move to endpoints or `auth_deps.py`
5. **One file per model** in `models/` and `repositories/`
6. **Thin endpoints** — a well-structured endpoint should be < 60 lines
