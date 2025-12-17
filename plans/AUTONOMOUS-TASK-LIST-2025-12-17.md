# Autonomous Task List - 2025-12-17

> Tasks Claude Code can execute autonomously without human intervention

## Completed This Session

1. **API Authentication Layer** - Added X-API-Key auth to Hydra Tools API (v2.5.0)
2. **Container Health Fix** - Connected hydra-tools-api to hydra-network (100% health)
3. **Draft Model Download** - Downloaded Llama-3.2-1B-Instruct-exl2-4.0bpw (1.2GB)
4. **Speculative Decoding Research** - Documented hardware limitation (70B+1B > 56GB VRAM)
5. **Prometheus Auth Metrics** - Added auth and HTTP request metrics (v2.6.0)
6. **Auth Unit Tests** - 25 tests for auth and metrics (all passing)
7. **Chapter Automation Test** - End-to-end story generation working (31.8s per chapter)
8. **Container Health Optimization** - 41 containers monitored, 100% healthy
9. **Grafana Auth Dashboard** - Created api-auth-metrics.json with 9 panels
10. **Docker Resource Review** - All containers healthy, 251GB RAM available
11. **Structured JSON Logging** - Added logging_config.py with request ID tracking
12. **ExLlamaV3 Research** - TP added in v0.0.6, TabbyAPI PR #173 pending
13. **Knowledge Base Update** - Updated inference-stack.md with ExLlamaV3 findings
14. **API Latency Profiling** - /hardware slowest (93ms SSH), others <10ms
15. **Prometheus Alert Rules** - Added 6 Hydra API alerts for auth failures, latency, errors

## Blocked (Needs User Input)

| Task | Blocking Reason |
|------|-----------------|
| Configure Home Assistant | Needs HA_TOKEN from user |
| Discord Webhook Setup | Needs webhook URL from user |
| Speculative Decoding | Hardware limitation (needs matched GPUs) |
| Gmail Integration | OAuth consent required |
| Google Calendar | OAuth consent required |

---

## AUTONOMOUS TASKS (No User Input Required)

### Priority 1: Code Quality & Testing

- [x] **Add unit tests for new API auth endpoints** ✓
  - Test `/auth/status` endpoint
  - Test `/auth/generate-key` endpoint
  - Test authentication middleware behavior
  - Verify exempt paths work correctly

- [x] **Fix any failing tests in test suite** ✓
  - Run `pytest tests/ -v` and fix failures
  - Ensure 100% pass rate maintained (25 tests passing)

- [ ] **Add type hints to modules missing them**
  - Check `src/hydra_tools/*.py` for missing type annotations
  - Add typing where needed for better IDE support

### Priority 2: Documentation Updates

- [x] **Update STATE.json with new features** ✓
  - Add API v2.6.0 info
  - Document auth endpoints and Prometheus metrics
  - Update session logs

- [x] **Update ROADMAP.md Quick Status** ✓
  - Update API version to 2.6.0
  - Add speculative decoding findings to learnings

- [ ] **Create API documentation**
  - Document all new endpoints in `/auth/*`
  - Update existing endpoint docs

### Priority 3: Infrastructure Improvements

- [x] **Optimize container health check intervals** ✓
  - Reviewed check frequencies (60s parallel checks = 0.6s total)
  - Added 5 new critical services (41 total monitored)
  - Fixed network routing for command-center

- [x] **Add Prometheus metrics for auth** ✓
  - Track auth success/failure rates (hydra_api_auth_requests_total)
  - Track API key usage patterns (by path_prefix)
  - Auth latency histograms (hydra_api_auth_latency_seconds)

- [x] **Review and optimize Docker resource limits** ✓
  - Checked memory limits on all containers (251GB available)
  - No resource starvation - top consumers: kokoro-tts 3.2GB, firecrawl-api 3.2GB

### Priority 4: Phase 12 (Empire of Broken Queens)

- [ ] **Automated quality scoring implementation**
  - Face consistency comparison with reference images
  - Style adherence scoring using CLIP embeddings
  - Technical quality checks (resolution, artifacts)

- [ ] **Scene parser improvements**
  - Add support for more markdown formats
  - Better emotion tag extraction
  - Handle edge cases in script parsing

- [x] **Test end-to-end chapter automation** ✓
  - Tested `/story/generate-chapter` endpoint
  - Generated full chapter with 3 scenes in 31.8s
  - Continuity editor found 3 issues (working correctly)

### Priority 5: Monitoring & Observability

- [x] **Create Grafana dashboard for API auth** ✓
  - Created api-auth-metrics.json with 9 panels
  - Auth success/failure over time
  - Request rate by endpoint, latency percentiles
  - HTTP status codes breakdown

- [x] **Review Alertmanager rules** ✓
  - Added 6 Hydra API alerts (HydraAPIDown, AuthFailuresHigh, AuthFailuresSpiking, LatencyHigh, ErrorRateHigh, RequestRateLow)
  - Added to prometheus/alert_rules.yml and reloaded

- [x] **Add structured logging** ✓
  - JSON log format via JSONFormatter class
  - Request ID tracking with request_id_ctx
  - Logs include method, path, status_code, duration_ms

### Priority 6: Knowledge Base Maintenance

- [x] **Review and update knowledge files** ✓
  - Updated inference-stack.md with ExLlamaV3 TP findings
  - Added migration path and configuration details

- [ ] **Archive old session logs**
  - Move completed session notes to archive
  - Keep only active context in main files

- [ ] **Consolidate duplicate documentation**
  - Find and merge redundant docs
  - Remove outdated files

### Priority 7: Performance Optimization

- [x] **Profile API endpoint latency** ✓
  - /hardware slowest (93ms - SSH to nodes)
  - /health, /diagnosis, /self-improvement all <10ms
  - Prometheus histograms tracking p50/p95/p99

- [ ] **Review memory usage patterns**
  - Check for memory leaks
  - Optimize large data structures
  - Implement lazy loading where possible

- [ ] **Benchmark inference routing**
  - Test RouteLLM classification accuracy
  - Measure routing overhead
  - Tune routing thresholds

### Priority 8: Research & Exploration

- [x] **Investigate ExLlamaV3 progress** ✓
  - Tensor parallel added in v0.0.6 (current: v0.0.18)
  - Heterogeneous GPU support requires manual gpu_split
  - TabbyAPI PR #173 pending merge
  - Recommendation: Stay on V2 until V3 TP stabilizes

- [ ] **Research alternative inference optimizations**
  - Continuous batching improvements
  - Flash attention updates
  - KV cache compression methods

- [ ] **Evaluate newer small models for draft**
  - Check for smaller Llama variants
  - Test Phi-3 as potential draft model

---

## Recommended Execution Order

1. **Immediate** (Next 30 mins):
   - Update STATE.json
   - Update ROADMAP.md
   - Run test suite

2. **Short-term** (Next 2-4 hours):
   - Add auth tests
   - Add Prometheus metrics
   - Create auth Grafana dashboard

3. **Medium-term** (Next 24 hours):
   - Quality scoring implementation
   - End-to-end chapter test
   - Knowledge base review

4. **Ongoing**:
   - Performance monitoring
   - Research tasks
   - Documentation updates

---

## Notes for Claude Code

- All tasks should produce observable results (code changes, test results, logs)
- Commit changes after significant completions
- Update todo list as tasks progress
- Document any blockers encountered
- Focus on tasks that improve system reliability first

*Generated: 2025-12-17T19:30:00Z*
*Last Updated: 2025-12-17T20:20:00Z*
