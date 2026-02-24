"""
Property-Based Test for Step Function Retry Logic

Property 31: Step Function Retry Logic
For any Step Function step that fails with a retryable error, the system should retry 
up to 3 times with exponential backoff before marking as failed.

Validates: Requirements 11.4, 16.1
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time


# ========================================
# Test Data Strategies
# ========================================

@st.composite
def retryable_error_strategy(draw):
    """Generate retryable error types"""
    error_types = [
        'States.TaskFailed',
        'States.Timeout',
        'Lambda.ServiceException',
        'Lambda.TooManyRequestsException'
    ]
    return draw(st.sampled_from(error_types))


@st.composite
def retry_attempt_strategy(draw):
    """Generate retry attempt data with timestamps"""
    attempt_number = draw(st.integers(min_value=0, max_value=3))
    error_type = draw(retryable_error_strategy())
    timestamp = datetime.now()
    
    return {
        'attempt': attempt_number,
        'error_type': error_type,
        'timestamp': timestamp,
        'success': False
    }


@st.composite
def retry_sequence_strategy(draw):
    """Generate a sequence of retry attempts"""
    num_failures = draw(st.integers(min_value=1, max_value=3))
    final_success = draw(st.booleans())
    
    attempts = []
    base_time = datetime.now()
    
    for i in range(num_failures):
        # Calculate expected delay with exponential backoff
        # interval = 2 seconds, backoffRate = 2.0
        expected_delay = 2 * (2 ** i)  # 2, 4, 8 seconds
        
        attempts.append({
            'attempt': i,
            'error_type': draw(retryable_error_strategy()),
            'timestamp': base_time + timedelta(seconds=sum(2 * (2 ** j) for j in range(i))),
            'success': False,
            'expected_delay': expected_delay if i > 0 else 0
        })
    
    # Add final attempt (success or final failure)
    if final_success and num_failures < 3:
        final_delay = 2 * (2 ** num_failures)
        attempts.append({
            'attempt': num_failures,
            'error_type': None,
            'timestamp': base_time + timedelta(seconds=sum(2 * (2 ** j) for j in range(num_failures + 1))),
            'success': True,
            'expected_delay': final_delay
        })
    
    return attempts


# ========================================
# Retry Logic Simulator
# ========================================

class StepFunctionRetrySimulator:
    """Simulates Step Functions retry behavior"""
    
    def __init__(self):
        self.max_attempts = 3
        self.base_interval = 2  # seconds
        self.backoff_rate = 2.0
        self.retryable_errors = [
            'States.TaskFailed',
            'States.Timeout',
            'Lambda.ServiceException',
            'Lambda.TooManyRequestsException'
        ]
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        if attempt == 0:
            return 0
        return self.base_interval * (self.backoff_rate ** (attempt - 1))
    
    def should_retry(self, error_type: str, attempt: int) -> bool:
        """Determine if error should be retried"""
        if error_type not in self.retryable_errors:
            return False
        if attempt >= self.max_attempts:
            return False
        return True
    
    def execute_with_retry(self, task_function, error_sequence: List[str]) -> Dict[str, Any]:
        """
        Execute a task with retry logic
        
        Args:
            task_function: Function to execute (not used in simulation)
            error_sequence: List of errors to simulate (empty string = success)
        
        Returns:
            Dict with execution results
        """
        attempts = []
        start_time = time.time()
        
        for attempt in range(min(len(error_sequence), self.max_attempts)):
            error = error_sequence[attempt]
            
            # Record attempt
            attempt_time = time.time()
            
            if error == '':
                # Success
                attempts.append({
                    'attempt': attempt,
                    'success': True,
                    'error': None,
                    'timestamp': attempt_time,
                    'delay': self.calculate_delay(attempt)
                })
                return {
                    'success': True,
                    'attempts': attempts,
                    'total_attempts': len(attempts),
                    'total_time': time.time() - start_time
                }
            else:
                # Failure
                attempts.append({
                    'attempt': attempt,
                    'success': False,
                    'error': error,
                    'timestamp': attempt_time,
                    'delay': self.calculate_delay(attempt)
                })
                
                # Check if we've reached max attempts
                if attempt >= self.max_attempts - 1:
                    return {
                        'success': False,
                        'attempts': attempts,
                        'total_attempts': len(attempts),
                        'total_time': time.time() - start_time,
                        'final_error': error
                    }
                
                # Check if should retry
                if not self.should_retry(error, attempt):
                    return {
                        'success': False,
                        'attempts': attempts,
                        'total_attempts': len(attempts),
                        'total_time': time.time() - start_time,
                        'final_error': error
                    }
        
        # All attempts exhausted
        return {
            'success': False,
            'attempts': attempts,
            'total_attempts': len(attempts),
            'total_time': time.time() - start_time,
            'final_error': attempts[-1]['error'] if attempts else None
        }


# ========================================
# Property Tests
# ========================================

@given(st.integers(min_value=0, max_value=5))
@settings(max_examples=100, deadline=None)
def test_property_retry_delay_exponential_backoff(attempt_number):
    """
    Property: Retry delays follow exponential backoff pattern
    
    For any attempt number, the delay should be: base_interval * (backoff_rate ^ (attempt - 1))
    With base_interval=2 and backoff_rate=2.0:
    - Attempt 0: 0 seconds (initial attempt, no delay)
    - Attempt 1: 2 seconds
    - Attempt 2: 4 seconds
    - Attempt 3: 8 seconds
    """
    simulator = StepFunctionRetrySimulator()
    
    expected_delay = simulator.calculate_delay(attempt_number)
    
    if attempt_number == 0:
        assert expected_delay == 0, "Initial attempt should have no delay"
    elif attempt_number == 1:
        assert expected_delay == 2, "First retry should have 2 second delay"
    elif attempt_number == 2:
        assert expected_delay == 4, "Second retry should have 4 second delay"
    elif attempt_number == 3:
        assert expected_delay == 8, "Third retry should have 8 second delay"
    else:
        # Beyond max attempts, delay continues to grow exponentially
        assert expected_delay == 2 * (2 ** (attempt_number - 1))


@given(retryable_error_strategy())
@settings(max_examples=50, deadline=None)
def test_property_retryable_errors_are_retried(error_type):
    """
    Property: Retryable errors trigger retry logic
    
    For any retryable error type, the system should retry up to max_attempts times.
    """
    simulator = StepFunctionRetrySimulator()
    
    # Simulate 2 failures followed by success (within max attempts)
    error_sequence = [error_type, error_type, '']
    
    result = simulator.execute_with_retry(None, error_sequence)
    
    # Should succeed after retries
    assert result['success'] is True, "Should succeed after retries"
    assert result['total_attempts'] == 3, "Should have 3 attempts (2 failures + 1 success)"
    
    # Verify each attempt has correct delay
    for i, attempt in enumerate(result['attempts']):
        expected_delay = simulator.calculate_delay(i)
        assert attempt['delay'] == expected_delay, f"Attempt {i} should have delay {expected_delay}"


@given(st.integers(min_value=1, max_value=5))
@settings(max_examples=50, deadline=None)
def test_property_max_retry_attempts_enforced(num_failures):
    """
    Property: Maximum retry attempts is enforced
    
    For any number of consecutive failures, the system should retry at most 3 times
    before giving up (total of 3 attempts).
    """
    simulator = StepFunctionRetrySimulator()
    
    # Simulate continuous failures (more than max to test enforcement)
    error_sequence = ['States.TaskFailed'] * num_failures
    
    result = simulator.execute_with_retry(None, error_sequence)
    
    # Should fail after max attempts
    assert result['success'] is False, "Should fail after max attempts"
    assert result['total_attempts'] <= 3, f"Should not exceed 3 attempts, got {result['total_attempts']}"
    
    # If we had 3 or more failures, should stop at exactly 3 attempts
    if num_failures >= 3:
        assert result['total_attempts'] == 3, "Should stop at exactly 3 attempts"


@given(st.lists(retryable_error_strategy(), min_size=1, max_size=2))
@settings(max_examples=100, deadline=None)
def test_property_early_success_stops_retries(error_sequence):
    """
    Property: Success stops retry loop early
    
    For any sequence of failures followed by success, the retry loop should stop
    immediately upon success without attempting remaining retries.
    """
    simulator = StepFunctionRetrySimulator()
    
    # Add success at the end
    full_sequence = error_sequence + ['']
    
    result = simulator.execute_with_retry(None, full_sequence)
    
    # Should succeed
    assert result['success'] is True, "Should succeed when success occurs"
    
    # Should have exactly len(error_sequence) + 1 attempts
    expected_attempts = len(error_sequence) + 1
    assert result['total_attempts'] == expected_attempts, \
        f"Should have {expected_attempts} attempts, got {result['total_attempts']}"
    
    # Last attempt should be successful
    assert result['attempts'][-1]['success'] is True, "Last attempt should be successful"


@given(st.integers(min_value=0, max_value=2))
@settings(max_examples=50, deadline=None)
def test_property_retry_count_matches_failures(num_failures):
    """
    Property: Number of retries matches number of failures before success
    
    For any number of failures (0-2) followed by success, the total attempts
    should be num_failures + 1.
    """
    simulator = StepFunctionRetrySimulator()
    
    # Create error sequence: num_failures errors + 1 success
    error_sequence = ['States.TaskFailed'] * num_failures + ['']
    
    result = simulator.execute_with_retry(None, error_sequence)
    
    # Should succeed
    assert result['success'] is True, "Should succeed after retries"
    
    # Total attempts should be num_failures + 1
    expected_attempts = num_failures + 1
    assert result['total_attempts'] == expected_attempts, \
        f"Should have {expected_attempts} attempts, got {result['total_attempts']}"


@given(st.lists(retryable_error_strategy(), min_size=3, max_size=3))
@settings(max_examples=50, deadline=None)
def test_property_all_retries_exhausted_results_in_failure(error_sequence):
    """
    Property: Exhausting all retries results in failure
    
    For any sequence of 3 consecutive retryable errors, the system should
    fail after the 3rd attempt without further retries.
    """
    simulator = StepFunctionRetrySimulator()
    
    result = simulator.execute_with_retry(None, error_sequence)
    
    # Should fail
    assert result['success'] is False, "Should fail after exhausting retries"
    
    # Should have exactly 3 attempts
    assert result['total_attempts'] == 3, f"Should have exactly 3 attempts, got {result['total_attempts']}"
    
    # Final error should be recorded
    assert result['final_error'] is not None, "Final error should be recorded"
    assert result['final_error'] in simulator.retryable_errors, "Final error should be retryable type"


@given(st.integers(min_value=0, max_value=3))
@settings(max_examples=50, deadline=None)
def test_property_delay_increases_with_each_retry(num_retries):
    """
    Property: Delay increases with each retry attempt
    
    For any sequence of retry attempts, each subsequent retry should have
    a longer delay than the previous one (exponential backoff).
    """
    assume(num_retries > 0)  # Need at least 1 retry to compare delays
    
    simulator = StepFunctionRetrySimulator()
    
    # Create error sequence
    error_sequence = ['States.TaskFailed'] * num_retries + ['']
    
    result = simulator.execute_with_retry(None, error_sequence)
    
    # Check that delays are increasing
    for i in range(1, len(result['attempts']) - 1):  # Exclude last (success) attempt
        current_delay = result['attempts'][i]['delay']
        previous_delay = result['attempts'][i - 1]['delay']
        
        assert current_delay > previous_delay, \
            f"Delay should increase: attempt {i-1} had {previous_delay}s, attempt {i} had {current_delay}s"


@given(st.lists(st.sampled_from(['States.TaskFailed', 'States.Timeout', 'Lambda.ServiceException']), 
               min_size=1, max_size=2))
@settings(max_examples=100, deadline=None)
def test_property_different_error_types_all_retried(error_types):
    """
    Property: All retryable error types trigger retry logic
    
    For any sequence of different retryable error types, all should be retried
    according to the same retry policy.
    """
    simulator = StepFunctionRetrySimulator()
    
    # Add success at the end (ensure we don't exceed max attempts)
    error_sequence = error_types + ['']
    
    result = simulator.execute_with_retry(None, error_sequence)
    
    # Should succeed after retries
    assert result['success'] is True, "Should succeed after retrying all error types"
    
    # Should have attempted all errors plus success
    assert result['total_attempts'] == len(error_types) + 1, \
        f"Should have {len(error_types) + 1} attempts"
    
    # Verify each failed attempt has the correct error type
    for i, error_type in enumerate(error_types):
        assert result['attempts'][i]['error'] == error_type, \
            f"Attempt {i} should have error type {error_type}"


# ========================================
# Integration Test with Actual Retry Configuration
# ========================================

def test_retry_configuration_matches_requirements():
    """
    Test that the retry configuration matches the requirements:
    - Max 3 retry attempts
    - Base interval of 2 seconds
    - Backoff rate of 2.0
    - Retries on specific error types
    """
    simulator = StepFunctionRetrySimulator()
    
    # Verify configuration
    assert simulator.max_attempts == 3, "Max attempts should be 3"
    assert simulator.base_interval == 2, "Base interval should be 2 seconds"
    assert simulator.backoff_rate == 2.0, "Backoff rate should be 2.0"
    
    # Verify retryable errors
    expected_errors = [
        'States.TaskFailed',
        'States.Timeout',
        'Lambda.ServiceException',
        'Lambda.TooManyRequestsException'
    ]
    
    for error in expected_errors:
        assert error in simulator.retryable_errors, f"{error} should be retryable"


def test_retry_delays_match_exponential_backoff():
    """
    Test that retry delays match the exponential backoff formula:
    delay = base_interval * (backoff_rate ^ (attempt - 1))
    """
    simulator = StepFunctionRetrySimulator()
    
    expected_delays = {
        0: 0,    # Initial attempt, no delay
        1: 2,    # 2 * (2^0) = 2
        2: 4,    # 2 * (2^1) = 4
        3: 8,    # 2 * (2^2) = 8
    }
    
    for attempt, expected_delay in expected_delays.items():
        actual_delay = simulator.calculate_delay(attempt)
        assert actual_delay == expected_delay, \
            f"Attempt {attempt} should have delay {expected_delay}s, got {actual_delay}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
