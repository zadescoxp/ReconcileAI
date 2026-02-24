# Step Functions Retry Logic Property Tests

## Overview

This directory contains property-based tests for AWS Step Functions retry logic, validating that the retry mechanism works correctly with exponential backoff as specified in Requirements 11.4 and 16.1.

## Test File

- `test_retry_logic_property.py` - Property-based tests for retry logic

## Property 31: Step Function Retry Logic

**Statement**: For any Step Function step that fails with a retryable error, the system should retry up to 3 times with exponential backoff before marking as failed.

**Validates**: Requirements 11.4, 16.1

## Retry Configuration

The Step Functions state machine is configured with the following retry policy:

- **Max Attempts**: 3
- **Base Interval**: 2 seconds
- **Backoff Rate**: 2.0 (exponential)
- **Retryable Errors**:
  - `States.TaskFailed`
  - `States.Timeout`
  - `Lambda.ServiceException`
  - `Lambda.TooManyRequestsException`

## Retry Delay Formula

The delay between retry attempts follows exponential backoff:

```
delay = base_interval * (backoff_rate ^ (attempt - 1))
```

Expected delays:
- Attempt 0 (initial): 0 seconds (no delay)
- Attempt 1 (first retry): 2 seconds
- Attempt 2 (second retry): 4 seconds
- Attempt 3 (third retry): 8 seconds

## Property Tests

### 1. Exponential Backoff Delay
Validates that retry delays follow the exponential backoff formula for all attempt numbers.

### 2. Retryable Errors Are Retried
Validates that all retryable error types trigger the retry mechanism up to max attempts.

### 3. Max Retry Attempts Enforced
Validates that the system stops after exactly 3 attempts, even if more failures occur.

### 4. Early Success Stops Retries
Validates that the retry loop stops immediately upon success without attempting remaining retries.

### 5. Retry Count Matches Failures
Validates that the number of retry attempts matches the number of failures before success.

### 6. All Retries Exhausted Results in Failure
Validates that exhausting all 3 retry attempts results in a final failure state.

### 7. Delay Increases With Each Retry
Validates that each subsequent retry has a longer delay than the previous one.

### 8. Different Error Types All Retried
Validates that all retryable error types are handled with the same retry policy.

### 9. Retry Configuration Matches Requirements
Validates that the retry configuration matches the specified requirements (3 attempts, 2s base, 2.0 backoff).

### 10. Retry Delays Match Exponential Backoff
Validates that actual retry delays match the exponential backoff formula for attempts 0-3.

## Running the Tests

```bash
# Run all property tests
python -m pytest tests/step-functions/test_retry_logic_property.py -v

# Run with hypothesis statistics
python -m pytest tests/step-functions/test_retry_logic_property.py -v --hypothesis-show-statistics

# Run specific test
python -m pytest tests/step-functions/test_retry_logic_property.py::test_property_retry_delay_exponential_backoff -v
```

## Test Coverage

The property tests generate 100+ test cases per property using Hypothesis, covering:
- All retry attempt numbers (0-5)
- All retryable error types
- Various failure sequences (1-5 consecutive failures)
- Success at different retry attempts
- Edge cases (max attempts, early success, all failures)

## Implementation Details

### StepFunctionRetrySimulator

A simulator class that mimics AWS Step Functions retry behavior:
- Calculates delays using exponential backoff formula
- Determines if errors should be retried
- Executes retry logic with configurable error sequences
- Tracks attempt history and timing

### Test Strategies

Hypothesis strategies generate:
- Retryable error types
- Retry attempt sequences
- Failure/success patterns
- Various attempt counts

## Integration with Step Functions

The retry configuration in `infrastructure/stacks/reconcile-ai-stack.ts` matches the tested behavior:

```typescript
const retryConfig = {
  errors: ['States.TaskFailed', 'States.Timeout', 'Lambda.ServiceException'],
  interval: cdk.Duration.seconds(2),
  maxAttempts: 3,
  backoffRate: 2.0,
};

extractTask.addRetry(retryConfig);
matchTask.addRetry(retryConfig);
detectTask.addRetry(retryConfig);
resolveTask.addRetry(retryConfig);
```

## AWS Free Tier Compliance

The retry configuration is optimized for AWS Free Tier:
- Limited to 3 retries to minimize state transitions
- Exponential backoff reduces API call frequency
- Stays within 4,000 state transitions/month limit

## References

- Requirements 11.4: Step Function retry logic
- Requirements 16.1: Lambda retry logic with exponential backoff
- Design Document: Error Handling section
- Infrastructure: `infrastructure/stacks/reconcile-ai-stack.ts`
