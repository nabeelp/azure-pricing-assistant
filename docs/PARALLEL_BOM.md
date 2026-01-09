# Parallel BOM Agent Implementation

## Overview
The BOM (Bill of Materials) Agent now runs in parallel with the Question Agent during the discovery phase. This allows users to continue answering questions while the BOM is being built in the background.

## Architecture

### Before (Synchronous)
```
User sends message → Question Agent processes → Wait for BOM Agent → Response sent
                                                  ↓
                                          BOM Agent runs (blocks)
                                                  ↓
                                          BOM items saved
```

### After (Parallel)
```
User sends message → Question Agent processes → Response sent immediately
                            ↓                           ↓
                    Trigger BOM update          User can continue
                            ↓
                    BOM Agent runs (async)
                            ↓
                    BOM items saved
                            ↓
                    Web UI polls and updates
```

## Key Components

### 1. Orchestrator (`src/core/orchestrator.py`)
- **`run_question_turn()`**: Modified to launch BOM updates with `asyncio.create_task()`
- **`_run_bom_update_background()`**: Background task wrapper that runs BOM updates
- **`get_bom_update_status()`**: Returns current BOM items and task status

### 2. Session Management (`src/core/models.py`)
- **`SessionData.bom_update_task`**: Tracks active background BOM update task
- Task reference is used to:
  - Check if update is in progress
  - Cancel overlapping updates
  - Clean up completed tasks

### 3. Web API (`src/web/handlers.py`, `src/web/interface.py`)
- **`/api/chat`**: Returns `bom_update_in_progress` flag
- **`/api/bom`**: Polls for current BOM items and update status

### 4. Web UI (`src/web/templates/index.html`)
- JavaScript polls `/api/bom` every 2 seconds
- BOM panel updates automatically as items are built
- Polling starts on page load and when BOM update is triggered
- Polling stops when conversation is complete

## Benefits

1. **Improved User Experience**: Users don't wait for BOM processing between questions
2. **Faster Conversations**: Question Agent returns immediately
3. **Progressive Disclosure**: BOM items appear as they're identified
4. **Scalability**: Can handle longer BOM processing times without blocking

## Error Handling

1. **Task Failures**: Background tasks catch exceptions and log errors without crashing
2. **Session Cleanup**: Task reference is cleared even if update fails
3. **Overlapping Updates**: New BOM updates cancel previous incomplete ones
4. **Network Errors**: Web UI handles polling errors gracefully

## Testing

See `tests/test_parallel_bom.py` for comprehensive test coverage:
- Background task execution without blocking
- BOM status checking
- Task cleanup on completion and error
- Question Agent continues while BOM updates

## Configuration

No configuration changes required. Parallel behavior is automatic when:
- `enable_incremental_bom=True` in `run_question_turn()` (default)
- BOM trigger conditions are met

## Performance

Typical timings:
- Question Agent response: < 1 second
- BOM Agent processing: 2-10 seconds (runs in background)
- Web UI polling interval: 2 seconds
- User can continue immediately without waiting

## Future Enhancements

Potential improvements:
1. WebSocket instead of polling for real-time updates
2. Incremental pricing calculation during BOM building
3. Progress indicators showing BOM update status
4. Optimistic UI updates before BOM completion
