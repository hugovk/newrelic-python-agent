# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import sys
import pytest

from newrelic.api.background_task import background_task
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction, record_log_event, ignore_transaction
from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_custom_metrics_outside_transaction import validate_custom_metrics_outside_transaction
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_event_count_outside_transaction import validate_log_event_count_outside_transaction
from testing_support.validators.validate_log_events import validate_log_events
from testing_support.validators.validate_log_events_outside_transaction import validate_log_events_outside_transaction

from testing_support.fixtures import (
    override_application_settings,
    validate_transaction_errors,
    validate_transaction_metrics,
)
from tests.agent_unittests.test_agent_protocol import HIGH_SECURITY
from tests.testing_support.fixtures import validate_internal_metrics


class CaplogHandler(logging.StreamHandler):
    """
    To prevent possible issues with pytest's monkey patching
    use a custom Caplog handler to capture all records
    """
    def __init__(self, *args, **kwargs):
        self.records = []
        super(CaplogHandler, self).__init__(*args, **kwargs)

    def emit(self, record):
        self.records.append(self.format(record))


@pytest.fixture(scope="function")
def logger():
    _logger = logging.getLogger("my_app")
    caplog = CaplogHandler()
    _logger.addHandler(caplog)
    _logger.caplog = caplog
    _logger.setLevel(logging.WARNING)
    yield _logger
    del caplog.records[:]
    _logger.removeHandler(caplog)


def set_trace_ids():
    txn = current_transaction()
    if txn:
        txn._trace_id = "abcdefgh12345678"
    trace = current_trace()
    if trace:
        trace.guid = "abcdefgh"


def exercise_logging(logger):
    set_trace_ids()

    logger.debug("A")
    logger.info("B")
    logger.warning("C")
    logger.error("D")
    logger.critical("E")
    
    assert len(logger.caplog.records) == 3

def exercise_record_log_event(message="A"):
    set_trace_ids()

    record_log_event(message, "ERROR")


_common_attributes_service_linking = {"timestamp": None, "hostname": None, "entity.name": "Python Agent Test (internal_logging)", "entity.guid": None}
_common_attributes_trace_linking = {"span.id": "abcdefgh", "trace.id": "abcdefgh12345678", **_common_attributes_service_linking}
_test_record_log_event_inside_transaction_events = [{"message": "A", "level": "ERROR", **_common_attributes_trace_linking}]

@reset_core_stats_engine()
def test_record_log_event_inside_transaction():
    @validate_log_events(_test_record_log_event_inside_transaction_events)
    @validate_log_event_count(1)
    @background_task()
    def test():
        exercise_record_log_event()
    
    test()


_test_record_log_event_outside_transaction_events = [{"message": "A", "level": "ERROR", **_common_attributes_service_linking}]

@reset_core_stats_engine()
def test_record_log_event_outside_transaction():
    @validate_log_events_outside_transaction(_test_record_log_event_outside_transaction_events)
    @validate_log_event_count_outside_transaction(1)
    def test():
        exercise_record_log_event()

    test()


_test_record_log_event_unknown_level_inside_transaction_events = [{"message": "A", "level": "UNKNOWN", **_common_attributes_trace_linking}]

@reset_core_stats_engine()
def test_record_log_event_unknown_level_inside_transaction():
    @validate_log_events(_test_record_log_event_unknown_level_inside_transaction_events)
    @validate_log_event_count(1)
    @background_task()
    def test():
        set_trace_ids()
        record_log_event("A")
    
    test()


_test_record_log_event_unknown_level_outside_transaction_events = [{"message": "A", "level": "UNKNOWN", **_common_attributes_service_linking}]

@reset_core_stats_engine()
def test_record_log_event_unknown_level_outside_transaction():
    @validate_log_events_outside_transaction(_test_record_log_event_unknown_level_outside_transaction_events)
    @validate_log_event_count_outside_transaction(1)
    def test():
        set_trace_ids()
        record_log_event("A")

    test()



@reset_core_stats_engine()
def test_record_log_event_empty_message_inside_transaction():
    @validate_log_event_count(0)
    @background_task()
    def test():
        exercise_record_log_event("")
    
    test()

@reset_core_stats_engine()
def test_record_log_event_empty_message_outside_transaction():
    @validate_log_event_count_outside_transaction(0)
    def test():
        exercise_record_log_event("")

    test()



_test_logging_unscoped_metrics = [
    ("Logging/lines", 3),
    ("Logging/lines/WARNING", 1),
    ("Logging/lines/ERROR", 1),
    ("Logging/lines/CRITICAL", 1),
]
_test_logging_inside_transaction_events = [
    {"message": "C", "level": "WARNING", **_common_attributes_trace_linking},
    {"message": "D", "level": "ERROR", **_common_attributes_trace_linking},
    {"message": "E", "level": "CRITICAL", **_common_attributes_trace_linking},   
]

@reset_core_stats_engine()
def test_logging_inside_transaction(logger):
    @validate_transaction_metrics(
        "test_application:test_logging_inside_transaction.<locals>.test",
        rollup_metrics=_test_logging_unscoped_metrics,
        background_task=True,
    )
    @validate_log_events(_test_logging_inside_transaction_events)
    @validate_log_event_count(3)
    @background_task()
    def test():
        exercise_logging(logger)
    
    test()


_test_logging_outside_transaction_events = [
    {"message": "C", "level": "WARNING", **_common_attributes_service_linking},
    {"message": "D", "level": "ERROR", **_common_attributes_service_linking},
    {"message": "E", "level": "CRITICAL", **_common_attributes_service_linking},   
]

@reset_core_stats_engine()
def test_logging_outside_transaction(logger):
    @validate_custom_metrics_outside_transaction(_test_logging_unscoped_metrics)
    @validate_log_events_outside_transaction(_test_logging_outside_transaction_events)
    @validate_log_event_count_outside_transaction(3)
    def test():
        exercise_logging(logger)

    test()



@reset_core_stats_engine()
def test_logging_newrelic_logs_not_forwarded(logger):
    @validate_log_event_count(0)
    @background_task()
    def test():
        nr_logger = logging.getLogger("newrelic")
        nr_logger.addHandler(logger.caplog)
        nr_logger.error("A")
        assert len(logger.caplog.records) == 1

    test()

@reset_core_stats_engine()
def test_ignored_transaction_logs_not_forwarded():
    @validate_log_event_count(0)
    @background_task()
    def test():
        ignore_transaction()
        exercise_record_log_event()

    test()


_test_log_event_truncation_events = [{"message": "A" * 32768, "level": "ERROR", **_common_attributes_trace_linking}]

@reset_core_stats_engine()
def test_log_event_truncation():
    @validate_log_events(_test_log_event_truncation_events)
    @validate_log_event_count(1)
    @background_task()
    def test():
        exercise_record_log_event("A" * 33000)

    test()

def test_settings():
    from newrelic.core.config import global_settings
    from newrelic.api.application import application_instance
    gs = global_settings()
    app_settings = application_instance().settings
    
    assert int(gs.event_harvest_config.harvest_limits.log_event_data / 12) == app_settings.event_harvest_config.harvest_limits.log_event_data

@reset_core_stats_engine()
@override_application_settings({'high_security': True})
def test_HSM_forwarding_disabled(logger):
    @validate_log_event_count(0)
    @background_task()
    def test():
        nr_logger = logging.getLogger("newrelic")
        nr_logger.addHandler(logger.caplog)
        nr_logger.warning("A")  #if HSM is on, this should not be forwarded
        assert len(logger.caplog.records) == 1

    test()

# _test_log_sampling_unscoped_metrics = [
#     ("Logging/lines", 900),
#     # ("Logging/Forwarding/Dropped", 67),
# ]

# @reset_core_stats_engine()
# def test_logs_dropped_inside_transaction(logger):
#     @validate_transaction_metrics(
#         "test_application:test_logs_dropped_inside_transaction.<locals>.test",
#         rollup_metrics=_test_log_sampling_unscoped_metrics,
#         background_task=True,
#     )
#     @validate_internal_metrics([("Logging/Forwarding/Dropped", 67)])
#     @background_task()
#     def test():
#         for _ in range(900):
#             logger.error("A")
#             # record_log_event("A", "ERROR")

#     test()
    





"""
# basic_inside
#     * validate log event
#     * validate transaction metrics
#     * validate all linking metadata
# basic_inside_under_different_level
# basic_outside
#     * validate log event
#     * validate custom metrics
#     * validate service linking metadata

# empty_message_inside
# empty_message_outside
# ignored_transaction
#     * no logs recorded
    * ========= Should metrics be recorded? ============
log_decorating_inside
    * URI encoding on entity.name
log_decorating_outside
    * URI encoding on entity.name
supportability_metrics_inside
supportability_metrics_outside
hsm_disabled/enabled
settings_matrix
# test_message_truncation
test_dropped
test_transaction_prioritized_over_outside
test_supportability_metrics_on_connect
test_log_level_unknown
test_harvest_limit_size (obey collector)
    * somehow test split payloads
test_exceeeded_payload_size
test_instrumentation_disabled
test_payload
"""
