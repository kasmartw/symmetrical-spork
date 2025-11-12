# Changelog - Mock API Integration

## [1.1.0] - 2025-11-12

### Added

#### Core Mock API System
- **`src/config.py`** - Centralized business logic configuration
  - 3 services: General, Specialized, Follow-up consultations
  - Operating hours: Mon-Fri, 9am-6pm with lunch break
  - Provider: Dr. Garcia (General Practice)
  - Location: Downtown Medical Center

- **`mock_api.py`** - Flask REST API server (335 lines)
  - `GET /services` - List all services
  - `GET /availability?service_id=X&date_from=Y` - Get time slots
  - `POST /appointments` - Create booking with validation
  - `GET /appointments/:id` - Get specific appointment
  - `GET /appointments` - List all (debugging)
  - `GET /health` - Health check
  - In-memory storage with counter
  - Realistic slot generation (14 days, 75% availability)
  - Email/phone validation
  - Alternative slots on conflicts

#### Agent Tools (src/tools.py)
- **`get_services_tool()`** - Fetch services from API
  - No parameters required
  - Returns formatted list of services
  - Error handling for API failures

- **`get_availability_tool(service_id, date_from?)`** - Get time slots
  - Required: service_id
  - Optional: date_from (YYYY-MM-DD)
  - Shows first 10 slots to avoid overwhelming LLM
  - Includes provider and location info

- **`create_appointment_tool(...)`** - Create appointment
  - 6 required parameters: service_id, date, start_time, client_name, client_email, client_phone
  - Full validation before API call
  - Returns confirmation number on success
  - Shows alternatives if slot unavailable

#### Tests (tests/unit/test_api_tools.py)
- **11 new unit tests** covering:
  - get_services_tool: 3 tests (success, error, empty)
  - get_availability_tool: 4 tests (success, with date, no slots, invalid service)
  - create_appointment_tool: 4 tests (success, unavailable, invalid email, API error)
- All tests use mocking (no real HTTP calls)
- **Result: 34 total unit tests passing**

#### Documentation
- **`QUICKSTART.md`** - Complete user guide
  - Prerequisites
  - Setup instructions
  - Two-terminal workflow
  - Example conversation
  - Available commands
  - Troubleshooting
  - Configuration tips

- **`MOCK_API_GUIDE.md`** - Technical documentation
  - Architecture diagrams
  - API endpoint specs
  - Configuration guide
  - Conversation flow
  - Testing instructions
  - Comparison v1 vs v2
  - Customization examples
  - Future enhancements

- **`run_mock_api.sh`** - Convenience script
  - Checks venv exists
  - Activates environment
  - Validates Flask installed
  - Starts mock API server

### Modified

#### src/agent.py
- **Imports:** Added 3 new API tools
- **Tools list:** Now 5 tools (was 2)
  - get_services_tool
  - get_availability_tool
  - validate_email_tool
  - validate_phone_tool
  - create_appointment_tool

- **System Prompt:** Complete rewrite (88 lines)
  - Full 11-step conversation flow
  - State-specific instructions
  - Tool usage guidelines
  - Clear rules and constraints
  - Context-aware prompts per state

#### src/tools.py
- **Imports:** Added `requests`, `json`, `Optional`, `config`
- **New Tools:** 3 API integration tools (189 lines)
- **Error Handling:**
  - RequestException catching
  - Generic Exception fallback
  - User-friendly error messages

### Test Results

```
✅ Unit Tests: 34 passed
   - Existing: 23 passed
   - New API Tools: 11 passed

⏱️  Execution Time: 14.25s

📊 Coverage: Maintained 90%+ requirement
```

---

## Usage

### Start the System

**Terminal 1 - Mock API:**
```bash
cd agent-appoiments-v2
source venv/bin/activate
python mock_api.py
```

**Terminal 2 - Agent:**
```bash
cd agent-appoiments-v2
source venv/bin/activate
python chat_cli.py
```

### Run Tests

```bash
# All unit tests
pytest tests/unit -v

# Only API tools tests
pytest tests/unit/test_api_tools.py -v

# With coverage
pytest --cov=src --cov-report=html
```

---

## Breaking Changes

None. The system is backward compatible with the existing validation tools.

---

## Migration from v1

If you were using the old `agent-appoiments/` project:

1. **Configuration:** `config.py` is very similar, just copy and adjust
2. **Mock API:** New version has more endpoints and better error handling
3. **Tools:** Same pattern with `@tool` decorator
4. **State Machine:** Now formal with explicit transitions
5. **Tests:** New TDD-first approach with 90%+ coverage

---

## Dependencies

No new external dependencies added. All using existing packages:
- `requests` - Already in requirements
- `flask` - Already in requirements
- `flask-cors` - Already in requirements

---

## Configuration

All configuration is in `src/config.py`:

```python
SERVICES = [...]          # Modify services offered
ASSIGNED_PERSON = {...}   # Change provider
LOCATION = {...}          # Update location
OPERATING_HOURS = {...}   # Adjust schedule
MOCK_API_PORT = 5000      # Change port if needed
```

**No code changes required** to customize the business logic!

---

## Files Changed Summary

### New Files (7)
1. `src/config.py` (51 lines)
2. `mock_api.py` (335 lines)
3. `run_mock_api.sh` (23 lines)
4. `tests/unit/test_api_tools.py` (279 lines)
5. `QUICKSTART.md` (389 lines)
6. `MOCK_API_GUIDE.md` (724 lines)
7. `CHANGELOG.md` (this file)

### Modified Files (2)
1. `src/tools.py` (+203 lines)
2. `src/agent.py` (+106 lines, -28 lines removed)

**Total:** 9 files, ~1,982 lines added

---

## Next Steps

Suggested improvements:

1. **Integration Tests:** Add end-to-end tests with real mock API
2. **PostgreSQL Integration:** Connect mock API to PostgresSaver
3. **More Services:** Add more service types in config
4. **SMS Notifications:** Integrate Twilio for confirmations
5. **Email Notifications:** Integrate SendGrid
6. **Rescheduling:** Add cancel/reschedule endpoints

---

## Credits

- **Original Design:** agent-appoiments v1
- **Mock API Enhancement:** agent-appoiments-v2 with TDD
- **LangGraph Version:** 1.0.3+
- **LangChain Version:** 1.0.5+

---

## License

MIT (same as project)
