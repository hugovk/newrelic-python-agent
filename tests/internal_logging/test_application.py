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
from newrelic.api.transaction import current_transaction
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


class CaplogHandler(logging.StreamHandler):
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


def exercise(logger):
    txn = current_transaction()
    if txn:
        txn._trace_id = "abcdefgh12345678"
    trace = current_trace()
    if trace:
        trace.guid = "abcdefgh"

    logger.debug("A")
    logger.info("B")
    logger.warning("C")
    logger.error("D")
    logger.critical("E")
    
    assert len(logger.caplog.records) == 3


_unscoped_metrics = [
    ("Logging/lines", 3),
    ("Logging/lines/WARNING", 1),
    ("Logging/lines/ERROR", 1),
    ("Logging/lines/CRITICAL", 1),
]

_common_attributes = {"timestamp": None, "span.id": "abcdefgh", "trace.id": "abcdefgh12345678", "hostname": None, "entity.name": "Python Agent Test (internal_logging)", "entity.guid": None}
_log_events = [
    {"message": "C", "level": "WARNING", **_common_attributes},
    {"message": "D", "level": "ERROR", **_common_attributes},
    {"message": "E", "level": "CRITICAL", **_common_attributes},   
]

@reset_core_stats_engine()
def test_logging_inside_transaction(logger):
    @validate_transaction_metrics(
        "test_application:test_logging_inside_transaction.<locals>.test",
        rollup_metrics=_unscoped_metrics,
        background_task=True,
    )
    @validate_log_events(_log_events)
    @validate_log_event_count(3)
    @background_task()
    def test():
        exercise(logger)
    
    test()


_common_attributes = {"timestamp": None, "hostname": None, "entity.name": "Python Agent Test (internal_logging)", "entity.guid": None}
_log_events = [
    {"message": "C", "level": "WARNING", **_common_attributes},
    {"message": "D", "level": "ERROR", **_common_attributes},
    {"message": "E", "level": "CRITICAL", **_common_attributes},   
]

@reset_core_stats_engine()
def test_logging_outside_transaction(logger):
    @validate_custom_metrics_outside_transaction(_unscoped_metrics)
    @validate_log_events_outside_transaction(_log_events)
    @validate_log_event_count_outside_transaction(3)
    def test():
        exercise(logger)

    test()


#@validate_log_events(1)
#@background_task()
#def test_skip_if_empty(logger):
#    logger.critical("")
#    #assert skip

"""
basic_inside
    * validate log event
    * validate transaction metrics
    * validate all linking metadata
basic_inside_under_different_level
basic_outside
    * validate log event
    * validate custom metrics
    * validate service linking metadata
empty_message_inside
empty_message_outside
ignored_transaction
    * no logs or metrics recorded
log_decorating_inside
    * URI encoding on entity.name
log_decorating_outside
    * URI encoding on entity.name
supportability_metrics_inside
supportability_metrics_outside
hsm_disabled/enabled
settings_matrix
test_message_truncation
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
