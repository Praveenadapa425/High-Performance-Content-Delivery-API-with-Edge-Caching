# Architecture

  If-None-Match: "a1b2c3d4e5f6..."
  
Server (matching ETag):
  HTTP/1.1 304 Not Modified
  (empty body - 0 bytes!)
  
Client: Uses cached version
```

## Security Architecture

### Access Token System

```
1. Create Token:
   POST /assets/{id}/access-token
   ├─ Generate 32-byte random token
   ├─ Set expiry: now + TOKEN_EXPIRY_SECONDS
   ├─ Store in PostgreSQL
   └─ Return to client

2. Use Token:
   GET /assets/private/{token}
   ├─ Query token from DB
   ├─ Validate:
   │  ├─ Token exists
   │  ├─ Not revoked
   │  ├─ Not expired (datetime.utcnow() < expires_at)
   └─ If valid: return content
   └─ If invalid: 403 Forbidden

3. Token Expiry:
   ├─ Configured per environment
   ├─ Default: 3600 seconds (1 hour)
   ├─ Adjustable per token
   └─ Automatic cleanup (optional job)
```

### Origin Protection

```
CDN Configuration:
├─ Origin Shield enabled
├─ IP whitelist
│  ├─ Only CDN IPs can access origin
│  └─ Blocks direct attacks
│
├─ Rate limiting
│  ├─ Per-IP limits
│  ├─ Protects upload endpoint
│  └─ Prevents DOS
│
└─ HTTPS/TLS
   ├─ Origin ↔ CDN: TLS
   ├─ Client ↔ CDN: TLS
   └─ Encryption in transit
```

## Scalability Considerations

### Horizontal Scaling

```
Multiple Origin Servers (Behind Load Balancer)
┌──────────────────────────────────────────┐
│         Load Balancer (HAProxy)          │
│  - Session persistence (optional)        │
│  - Health checks                         │
│  - Request distribution                  │
└─┬────────────────────────────────────────┘
  │
  ├─► Origin Server 1 (FastAPI)
  ├─► Origin Server 2 (FastAPI)
  ├─► Origin Server 3 (FastAPI)
  │
  ├─ Shared PostgreSQL (read replicas)
  │
  └─ Shared Object Storage (MinIO/S3)
```

### Database Optimization

```
PostgreSQL:
├─ Indexes on frequently queried columns
│  ├─ Asset.id (primary key)
│  ├─ AccessToken.token
│  └─ AssetVersion.asset_id
│
├─ Partitioning (optional for scale)
│  ├─ Partition AccessToken by month
│  └─ Archive old versions
│
└─ Connection pooling
   ├─ SQLAlchemy pool_size=20
   └─ max_overflow=40
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
- Streaming downloads
- Signed URLs for direct access

## Monitoring & Observability

### Metrics to Track

```
Performance Metrics:
├─ Response time (p50, p95, p99)
├─ Cache hit ratio (>95% target)
├─ Error rates (4xx, 5xx)
├─ Request throughput (req/sec)
└─ Bandwidth saved by caching

Business Metrics:
├─ Assets uploaded (count)
├─ Total storage used (GB)
├─ Private vs public asset split
└─ Token generation rate
```

### Logging

```
Structure:
├─ Request logging
│  ├─ Timestamp
│  ├─ Method, Path, Status
│  ├─ Response time
│  ├─ Cache status
│  └─ User agent
│
└─ Application logging
   ├─ Upload operations
   ├─ Token creation/validation
   ├─ CDN purge operations
   └─ Errors and exceptions
```

## Disaster Recovery

### Backup Strategy

```
1. Database Backups
   ├─ Frequency: Daily
   ├─ Retention: 30 days
   ├─ Location: S3 backup bucket
   └─ Restore time: <5 minutes

2. Asset Backups
   ├─ Frequency: Continuous (S3 versioning)
   ├─ Retention: Per bucket policy
   ├─ Location: Multi-region (optional)
   └─ Restore time: <1 minute

3. Configuration Backups
   ├─ Frequency: On change
   ├─ Location: Git repo
   └─ Version control enabled
```

## Summary

This architecture prioritizes:
1. **Performance**: Multi-tier caching, conditional requests
2. **Scalability**: Stateless origin servers, distributed caching
3. **Reliability**: Database backups, monitoring
4. **Security**: Token-based access, origin protection
5. **Cost-efficiency**: Reduced bandwidth, origin load
