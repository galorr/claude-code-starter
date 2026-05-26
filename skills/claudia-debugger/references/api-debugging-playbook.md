# API Debugging Playbook

How Claudia debugs HTTP/API errors (403, 401, 500, etc.). Read this when the investigation starts with a failing request, an HTTP error response, or a curl command.

## Phase A — Request Anatomy

Decompose the failing request into layers:

1. **URL & routing**: target host, path, HTTP method
2. **Headers**: origin, content-type, auth headers, custom headers (x-access-token, x-source-id, etc.)
3. **Cookies**: session cookies, identity cookies, bot-detection cookies (PerimeterX `_px3`, etc.)
4. **Body/payload**: GraphQL operation name, variables, query; REST body
5. **Identity consistency**: check that all identity signals (cookies, JWT, headers) refer to the **same user/session** — mismatches are a top cause of 403s

### JWT Token Analysis

When a JWT is present (Authorization header, cookie, or custom header):

```bash
# Decode JWT payload (middle segment) without verification
echo '<JWT_PAYLOAD_SEGMENT>' | tr '_-' '/+' | base64 -d 2>/dev/null | jq .

# Check token expiry (macOS)
date -r $(echo 'JWT_PAYLOAD' | tr '_-' '/+' | base64 -d 2>/dev/null | jq -r .exp)
# Check token expiry (Linux)
date -d @$(echo 'JWT_PAYLOAD' | tr '_-' '/+' | base64 -d 2>/dev/null | jq -r .exp)
```

Extract and report:
- `sub` / `email` — who the token identifies
- `exp` / `iat` — is the token expired?
- Platform/entitlement claims (e.g., `platforms`, `roles`, `scopes`, `permissions`)
- Session type, tenant ID, group ID
- Issuer (`iss`) and audience (`aud`)

**Red flags:**
- Token `email` differs from cookie-based identity — session mismatch
- `exp` is in the past — expired token
- Platform/entitlement claims are restrictive (e.g., `FREE` tier only)
- Session type indicates limited access

## Phase B — Response Analysis

Determine WHERE the rejection happens:

| Signal | Meaning |
|---|---|
| HTML error page / generic 403 | Gateway/proxy/WAF rejection (CDN, nginx, PerimeterX) |
| JSON with `errors[]` array + GraphQL `path` | **Resolver-level** rejection — the request reached the app |
| JSON with `error` + `statusCode` | REST controller/middleware rejection |
| `extensions.code` = `FORBIDDEN` | Authorization guard or resolver denied access |
| `extensions.code` = `UNAUTHENTICATED` | Token missing, invalid, or expired |

**Key insight**: If the response is a structured GraphQL error with a `path`, the request passed through the API gateway and was rejected by application-level authorization. Focus on the app code, not infra.

## Phase C — Codebase Trace

Once you know the failing endpoint/resolver, trace through the code:

1. **Find the resolver/controller**: search for the operation name or route path
2. **Identify guards & interceptors**: look for `@UseGuards(...)` and `@UseInterceptors(...)` decorators on the method and class. Execution order is left to right.
3. **Trace each guard**: for each guard in the chain, read its `canActivate()` method:
   - What claims/headers does it check?
   - What conditions return `false` (which triggers a 403)?
   - Does it call external services (entitlement APIs, feature flags)?
4. **Trace interceptors**: check if any can throw or modify the response
5. **Check middleware**: look for global or route-level middleware that runs before guards

### NestJS Guard Pattern

```typescript
// Guard returns false → NestJS throws 403 Forbidden automatically
canActivate(context: ExecutionContext): boolean {
  const token = extractToken(context);
  const platforms = decode(token)?.platforms;
  return !platforms?.includes('FREE') || !requiresElevatedAccess;
}
```

When a guard returns `false`, NestJS generates a generic `{ "message": "Forbidden resource", "statusCode": 403 }`. The app may wrap this in a GraphQL error format.

### NestJS Data Flow Tracing

For service-level bugs (wrong output, missing field, wrong calculation):

1. Identify the entry point: controller method → service method → downstream calls
2. For each call, check: input type expected vs. actual value passed vs. interface definition
3. Check interface / DTO / type files — confirm field names, optionality (`?`), and types match across all layers
4. Watch for string/number boundary issues — MongoDB IDs are strings; token IDs may be numbers. Convert at the service boundary with `String()` / `Number()`.

## Phase D — Environment Comparison

When the same request works in one environment but not another:

1. **Find config files**: search for `config.staging.ts`, `config.prod.ts`, `config.*.ts`
2. **Compare configs** focusing on:
   - Entitlement/permission service URLs
   - Feature flags and toggles
   - SSL/TLS settings
   - Rate limits
   - External service endpoints
3. **Check feature flags**: search for `featureFlag`, `isEnabled`, `toggle`, `LaunchDarkly`, `split` in relevant files
4. **Check deployed versions**: staging and prod may run different code

## Common Error Causes — Quick Reference

### 403 Forbidden

| Cause | How to identify |
|---|---|
| Expired JWT | `exp` claim < current timestamp |
| Token/cookie identity mismatch | Different emails in JWT vs cookies |
| Insufficient platform entitlement | `platforms`, `scopes`, or `roles` missing required values |
| Guard blocking specific operation | Guard checks request params against user tier |
| CORS / origin rejection | `origin` header not in server's allowed list |
| Bot detection (PerimeterX, Cloudflare) | HTML response instead of JSON; `_px3` cookie flagged |
| Rate limiting | Response includes `Retry-After` header |
| Environment-specific config | Feature enabled in staging but not prod |

### 401 Unauthorized

| Cause | How to identify |
|---|---|
| Missing auth header | No `Authorization` header in request |
| Malformed token | Token doesn't have 3 dot-separated segments |
| Invalid signature | Token was issued by a different auth provider |
| Token expired | `exp` < now (check clock skew too) |

### 500 Internal Server Error

| Cause | How to identify |
|---|---|
| Unhandled null/undefined | Stack trace shows `Cannot read properties of undefined` |
| Downstream service timeout | Error wraps a connection timeout or ECONNREFUSED |
| Database connection exhaustion | Pool errors, connection limit reached |
| Type mismatch at runtime | Expected string got number (or vice versa) at a boundary |

## Useful Commands

```bash
# Decode JWT without external tools
echo 'JWT_PAYLOAD' | tr '_-' '/+' | base64 -d 2>/dev/null | jq .

# Find all guards in a NestJS project
grep -r "@UseGuards" --include="*.ts" -l

# Find all interceptors
grep -r "@UseInterceptors" --include="*.ts" -l

# Find environment configs
find . -name "config.*.ts" -o -name "*.config.ts" | head -20
```

## Self-Validation Checklist

Before reporting findings from an API debugging session:

1. Did I decode and analyze all tokens in the request?
2. Did I check for identity mismatches across cookies, headers, and JWT?
3. Did I determine if the rejection is at gateway level or application level?
4. Did I trace through every guard/interceptor in the chain?
5. Did I compare environment configs when staging vs prod differs?
6. Did I provide a concrete verification step the user can try?
