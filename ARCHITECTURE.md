# Architecture

## System Overview

The High-Performance Content Delivery API is designed to minimize latency and maximize cache hit rates through strategic use of HTTP caching, CDN integration, and object storage.

### Architecture Diagram

```mermaid
graph TB
    C["CLIENTS (Web Browsers, Mobile Apps, API Consumers)"]

    subgraph CDNLayer["CDN Edge Servers (Cloudflare, etc.)"]
        CE["Cache Layer 1 · Origin Shield · DDoS Protection · Compression"]
    end

    subgraph OriginLayer["Origin API Server (FastAPI)"]
        API["Request Routing · ETag Generation · Token Validation"]
    end

    DB[("PostgreSQL DB — Asset Metadata · Versions · Access Tokens")]
    Redis[("Redis Cache — Future Add-on · Not Enabled")]
    S3[("Object Storage — MinIO / S3 — Asset Files · Versioned Objects")]

    C -->|HTTPS/HTTP| CDNLayer
    C -->|HTTPS/HTTP| OriginLayer
    CDNLayer <-->|Origin Pull| OriginLayer
    OriginLayer --> DB
    OriginLayer -.->|not enabled| Redis
    OriginLayer --> S3
```

## Request Flow

### 1. Public Asset Download (Cached)

```mermaid
flowchart TD
    A["Client: GET /assets/asset_id/download"] --> B{"CDN Edge"}
    B -->|"Cache HIT"| C["Return cached response (0-10ms)"]
    B -->|"Cache MISS"| D["Origin API Server"]
    D --> E["Query PostgreSQL for asset metadata"]
    E --> F{"If-None-Match header?"}
    F -->|"ETag matches"| G["Return 304 Not Modified — 0 bytes"]
    F -->|"No match"| H["Download from MinIO/S3"]
    H --> I["Set Cache-Control: public, s-maxage=3600, max-age=60"]
    I --> J["Return 200 OK + ETag + Last-Modified headers"]
    J --> K["CDN caches 1hr (edge) / 60s (browser)"]
```

**Response Headers:**
```
HTTP/1.1 200 OK
ETag: "a1b2c3d4e5f6..."
Last-Modified: Wed, 10 Jan 2024 10:00:00 GMT
Cache-Control: public, s-maxage=3600, max-age=60
Content-Type: application/pdf
Content-Length: 1024000
X-Content-Type-Options: nosniff
```

### 2. Conditional Request (304 Not Modified)

```mermaid
flowchart TD
    A["Client: GET with If-None-Match: etag-value"] --> B{"CDN Edge"}
    B -->|"Cache HIT"| C["Return 304 Not Modified — empty body"]
    B -->|"Cache MISS"| D["Origin API Server"]
    D --> E["Query PostgreSQL for asset"]
    E --> F{"ETag match?"}
    F -->|"Match"| G["Return 304 Not Modified — 0 bytes — 99%+ bandwidth saved"]
    F -->|"No match"| H["Return 200 OK with full content"]
    G --> I["Client uses cached version"]
```

**Benefits:**
- Zero bytes transmitted
- Reduces bandwidth by 99%+
- Client uses cached version
- Very low latency response time at the edge

### 3. Private Asset Access (Token-Based)

```mermaid
flowchart TD
    A["Client: GET /assets/private/token"] --> B["CDN: Not cached — pass through to origin"]
    B --> C["Origin API Server"]
    C --> D["Query AccessToken from PostgreSQL"]
    D --> E{"Token valid?"}
    E -->|"exists + not revoked + not expired"| F["Query asset metadata"]
    F --> G["Download content from MinIO/S3"]
    G --> H["Return 200 OK — Cache-Control: private, no-store"]
    E -->|"Invalid or expired"| I["Return 403 Forbidden"]
```

**Response Headers (Private):**
```
HTTP/1.1 200 OK
ETag: "x1y2z3a4b5c6..."
Cache-Control: private, no-store, no-cache, must-revalidate
Content-Type: application/pdf
X-Content-Type-Options: nosniff
```

### 4. Asset Upload Flow

```mermaid
flowchart TD
    A["Client: POST /assets/upload"] --> B["Origin API Server"]
    B --> C["Receive file bytes"]
    C --> D["Calculate SHA-256 ETag from content"]
    D --> E["Upload to MinIO/S3"]
    E --> F["Store metadata in PostgreSQL"]
    F --> G["Asset ID, Filename, MIME type, File size, ETag, Object key, Timestamps"]
    G --> H["Return 201 Created with full asset metadata"]
```

### 5. Asset Publishing (Versioning)

```mermaid
flowchart TD
    A["Client: POST /assets/asset_id/publish"] --> B["Origin API Server"]
    B --> C["Query current asset from PostgreSQL"]
    C --> D["Download current content from S3"]
    D --> E["Create versioned key: versions/id/vN/filename"]
    E --> F["Upload immutable copy to S3"]
    F --> G["Store AssetVersion in PostgreSQL"]
    G --> H["Increment asset version counter"]
    H --> I{"CDN purge enabled?"}
    I -->|"Yes"| J["Trigger Cloudflare cache purge"]
    I -->|"No"| K["Return 200 OK with version_id, version_number, etag, url"]
    J --> K
```

## Caching Strategy

### Three-Tier Cache Architecture

```mermaid
graph TB
    subgraph T1["Tier 1 — Browser Cache (Client-side)"]
        B1["max-age: 60s · Revalidates with ETag after 60s · Saves bandwidth on repeat visits"]
    end

    subgraph T2["Tier 2 — CDN Edge Cache (Cloudflare)"]
        B2["Mutable content: s-maxage=3600 (1hr) · Versioned immutable: max-age=31536000 (1yr) · Origin shield · Cache hit target >95%"]
    end

    subgraph T3["Tier 3 — Origin Server (Metadata Lookup)"]
        B3["Pre-computed SHA-256 ETags in PostgreSQL · No hash recalculation per request · Fast single-query metadata fetch"]
    end

    T1 -->|"Cache miss or revalidation"| T2
    T2 -->|"Cache miss"| T3
```

### Cache Directives

#### Immutable Content (Versioned)
```
Cache-Control: public, max-age=31536000, immutable
```
- Cached for 1 year (31536000 seconds)
- Never expires
- Immutable flag prevents revalidation
- Safe for versioned URLs

#### Mutable Content (Latest)
```
Cache-Control: public, s-maxage=3600, max-age=60
```
- Browser: 60 seconds (max-age)
- CDN: 3600 seconds (s-maxage)
- After browser cache expires, revalidates
- CDN holds longer for efficiency

#### Private Content
```
Cache-Control: private, no-store, no-cache, must-revalidate
```
- Not cached by CDN
- Not stored in browser cache
- Always revalidates
- Required for sensitive content

## ETag Strategy

### Strong ETag Generation

```python
import hashlib

def generate_etag(content: bytes) -> str:
    """Generate strong ETag using SHA-256"""
    hash_value = hashlib.sha256(content).hexdigest()
    return f'"{hash_value}"'
```

**Advantages:**
- SHA-256 provides collision resistance
- Changes for any byte modification
- Stored in DB (no recalculation)
- Used for 304 Not Modified responses

### ETag-Based Conditional Requests

```
Client: GET /assets/123
Server Response:
  HTTP/1.1 200 OK
  ETag: "a1b2c3d4e5f6..."
  
Client (later):
  GET /assets/123
  If-None-Match: "a1b2c3d4e5f6..."
  
Server (matching ETag):
  HTTP/1.1 304 Not Modified
  (empty body - 0 bytes!)
  
Client: Uses cached version
```

## Security Architecture

### Access Token System

```mermaid
flowchart TD
    subgraph Create["1 — Create Token"]
        CT1["POST /assets/asset_id/access-token"]
        CT2["Generate secrets.token_urlsafe(32)"]
        CT3["Set expiry: now + TOKEN_EXPIRY_SECONDS"]
        CT4["Store in PostgreSQL and return to client"]
        CT1 --> CT2 --> CT3 --> CT4
    end

    subgraph Use["2 — Use Token"]
        UT1["GET /assets/private/token"]
        UT2{"Validate"}
        UT3["Return 200 OK with asset content"]
        UT4["Return 403 Forbidden"]
        UT1 --> UT2
        UT2 -->|"exists AND not revoked AND not expired"| UT3
        UT2 -->|"any check fails"| UT4
    end

    subgraph Expiry["3 — Token Expiry"]
        E1["Default: 3600s (1hr) · Adjustable per token · Validated via datetime.utcnow() check"]
    end
```

### Origin Protection

```mermaid
graph TD
    CDN["CDN Configuration"]
    CDN --> OS["Origin Shield — only CDN IPs reach origin — blocks direct attacks"]
    CDN --> RL["Rate Limiting — per-IP limits — protects upload endpoint — prevents DoS"]
    CDN --> TLS["HTTPS / TLS — Origin to CDN: TLS — Client to CDN: TLS — encryption in transit"]
```

## Scalability Considerations

### Horizontal Scaling

```mermaid
graph TB
    LB["Load Balancer (HAProxy) — health checks · session persistence · request distribution"]
    API1["Origin Server 1 (FastAPI)"]
    API2["Origin Server 2 (FastAPI)"]
    API3["Origin Server 3 (FastAPI)"]
    DB[("PostgreSQL + Read Replicas")]
    S3[("Shared Object Storage — MinIO / S3")]

    LB --> API1
    LB --> API2
    LB --> API3
    API1 & API2 & API3 --> DB
    API1 & API2 & API3 --> S3
```

### Database Optimization

```mermaid
graph TD
    PG["PostgreSQL Optimizations"]
    PG --> IDX["Indexes — Asset.id (PK) · AccessToken.token · AssetVersion.asset_id"]
    PG --> PART["Partitioning (optional) — AccessToken by month · archive old versions"]
    PG --> POOL["Connection Pooling — SQLAlchemy pool_size=20 · max_overflow=40"]
```

## Performance Optimizations

### 1. ETag Caching
- ETags pre-calculated during upload
- No expensive hash calculations per request
- Direct database lookup

### 2. Conditional Response Handling
- Fast string comparison
- Return 304 with empty body
- Saves 99% of bandwidth

### 3. CDN Configuration
- Aggressive caching for public content
- Origin shield to reduce backend load
- Cache purging on updates (optional)

### 4. Object Storage
- Async uploads to S3/MinIO
- Buffered downloads (current implementation)
- Signed URLs for direct access

## Monitoring & Observability

### Metrics to Track

**Performance Metrics:**
- Response time (p50, p95, p99)
- Cache hit ratio (>95% target)
- Error rates (4xx, 5xx)
- Request throughput (req/sec)
- Bandwidth saved by caching

**Business Metrics:**
- Assets uploaded (count)
- Total storage used (GB)
- Private vs public asset split
- Token generation rate

### Logging

**Request Logging:** Timestamp · Method · Path · Status · Response time · Cache status · User agent

**Application Logging:** Upload operations · Token creation/validation · CDN purge operations · Errors and exceptions

## Disaster Recovery

### Backup Strategy

1. **Database Backups** — Daily · 30-day retention · S3 backup bucket · Restore time: <5 minutes
2. **Asset Backups** — Continuous via S3 versioning · Per-bucket retention policy · Multi-region optional · Restore time: <1 minute
3. **Configuration Backups** — On change · Stored in Git · Version controlled

## Summary

This architecture prioritizes:
1. **Performance**: Multi-tier caching, conditional requests
2. **Scalability**: Stateless origin servers, distributed caching
3. **Reliability**: Database backups, monitoring
4. **Security**: Token-based access, origin protection
5. **Cost-efficiency**: Reduced bandwidth, origin load