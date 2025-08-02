# Enhanced Validation Workflow - Addressing Gaps

## Timeout & Back-pressure Handling

### Problem
Original wrapper didn't specify repair call timeouts, risking hung processes.

### Solution
```python
async def validate_and_repair(self, llm_response, model_client, **kwargs) -> BaseModel:
    # 1. Extract function call
    # 2. Initial validation
    
    if validation_fails:
        start_time = time.time()
        try:
            repair_result = await asyncio.wait_for(
                self._attempt_repair(model_client, error, original_response),
                timeout=self.repair_timeout_ms / 1000
            )
        except asyncio.TimeoutError:
            self.observability.increment('repair_timeout')
            raise OutputParserError("Repair attempt timed out")
        
        repair_duration = (time.time() - start_time) * 1000
        self.observability.record_time('repair_roundtrip_ms', repair_duration)
```

### Configuration
- `REPAIR_TIMEOUT_MS=5000` (default 5 seconds)
- `repair_timeout` metric for monitoring

## Partial Success Handling

### Problem
Current design retries even when only optional fields fail validation.

### Solution
```python
def _categorize_validation_errors(self, validation_error: ValidationError) -> dict:
    """Categorize errors by field requirement level"""
    required_field_errors = []
    optional_field_errors = []
    
    for error in validation_error.errors():
        field_path = error['loc']
        field_name = field_path[-1] if field_path else None
        
        if self._is_required_field(field_name):
            required_field_errors.append(error)
        else:
            optional_field_errors.append(error)
    
    return {
        'required_errors': required_field_errors,
        'optional_errors': optional_field_errors,
        'needs_repair': len(required_field_errors) > 0
    }

async def validate_and_repair(self, llm_response, model_client, **kwargs) -> BaseModel:
    try:
        return self.pydantic_model.model_validate(arguments)
    except ValidationError as e:
        error_analysis = self._categorize_validation_errors(e)
        
        if not error_analysis['needs_repair']:
            # Only optional field errors - log warning but proceed
            self.observability.increment('repair_skipped')
            self.observability.log_validation_failure(
                model_name, 'optional_fields_only', error_analysis, log_level='WARN'
            )
            # Return partial model with defaults for missing optional fields
            return self._create_partial_model(arguments)
        
        # Required field errors - proceed with repair
        return await self._attempt_repair(...)
```

### Benefits
- Reduces unnecessary repair calls
- Improves performance for minor validation issues
- Tracks skipped repairs for monitoring

## Schema Evolution & Deprecation

### Problem
Schema versioning stub exists but no deprecation strategy.

### Solution
```python
def _check_schema_version(self, arguments: dict) -> None:
    """Validate schema version compatibility with deprecation support"""
    schema_version = arguments.get('schema_version')
    
    if schema_version is None:
        raise OutputParserError("Missing required schema_version field")
    
    min_version = int(os.getenv('MIN_ACCEPTED_SCHEMA_VERSION', '1'))
    max_version = int(os.getenv('MAX_ACCEPTED_SCHEMA_VERSION', '1'))
    
    if schema_version < min_version:
        self.observability.increment('schema_version_rejected')
        raise OutputParserError(
            f"Schema version {schema_version} is deprecated. "
            f"Minimum supported version: {min_version}. "
            f"Please update your agent to use schema version {max_version}."
        )
    
    if schema_version > max_version:
        self.observability.increment('schema_version_rejected')
        raise OutputParserError(
            f"Schema version {schema_version} is not supported. "
            f"Maximum supported version: {max_version}."
        )

# In validate_and_repair method:
def validate_and_repair(self, llm_response, model_client, **kwargs) -> BaseModel:
    arguments = self._extract_function_call(llm_response)
    
    # Check schema version first - fail fast for incompatible versions
    self._check_schema_version(arguments)
    
    # Proceed with validation...
```

### Configuration
- `MIN_ACCEPTED_SCHEMA_VERSION=1` (reject older schemas)
- `MAX_ACCEPTED_SCHEMA_VERSION=1` (reject future schemas)
- Clear error messages with upgrade instructions

## Observability Volume Control

### Problem
Printing every failure floods production logs.

### Solution
```python
class ObservabilityHandler:
    def __init__(self):
        self.counters = defaultdict(int)
        self.histograms = defaultdict(list)
        self.log_level = os.getenv('VALIDATION_LOG_LEVEL', 'INFO')
        self.sample_rate = float(os.getenv('VALIDATION_LOG_SAMPLE_RATE', '0.1'))
        self.last_aggregation = time.time()
        self.aggregation_interval = 60  # seconds
        
    def should_log_verbose(self) -> bool:
        """Sample logging based on configured rate"""
        return random.random() < self.sample_rate
        
    def log_validation_failure(self, model: str, error_type: str, details: dict, log_level: str = "INFO"):
        """Log with level and sampling control"""
        # Always increment counters
        self.increment(f'validation_failed_{error_type}')
        
        if log_level == "DEBUG" and self.log_level != "DEBUG":
            return  # Skip verbose logs in production
            
        if log_level == "INFO" or self.should_log_verbose():
            # Log either at INFO level or sampled DEBUG
            logger.log(log_level, {
                'event': 'validation_failure',
                'model': model,
                'error_type': error_type,
                'details': details,
                'timestamp': time.time()
            })
    
    def log_aggregated_metrics(self):
        """Periodic aggregated logging for production monitoring"""
        now = time.time()
        if now - self.last_aggregation >= self.aggregation_interval:
            logger.info({
                'event': 'validation_metrics_summary',
                'interval_seconds': self.aggregation_interval,
                'counters': dict(self.counters),
                'timestamp': now
            })
            self.last_aggregation = now
```

### Log Level Strategy
- **DEBUG**: All failures logged with full details (development)
- **INFO**: Aggregated counts + sampled failures (production)
- **WARN**: Only critical issues and partial successes
- **ERROR**: Schema compatibility and timeout issues

### Configuration
- `VALIDATION_LOG_LEVEL=INFO` (production default)
- `VALIDATION_LOG_SAMPLE_RATE=0.1` (sample 10% of failures for details)

## Updated Success Criteria

1. **Timeout Handling**: Repair calls respect `REPAIR_TIMEOUT_MS` and increment timeout metric
2. **Partial Success**: Optional field failures skip repair and log warnings  
3. **Schema Evolution**: Version checks provide actionable error messages
4. **Log Volume**: Production logging respects level and sampling configuration
5. **Metrics Coverage**: All new counters tracked and reported

## Implementation Priority

1. **Schema version checks** (fail-fast for compatibility)
2. **Partial success handling** (performance improvement)
3. **Timeout handling** (reliability)
4. **Log volume control** (production readiness)

These enhancements make the validation wrapper production-ready with proper error handling, performance optimization, and observability control.