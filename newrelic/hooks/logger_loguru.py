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

from newrelic.api.application import application_instance
from newrelic.api.transaction import current_transaction, record_log_event
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.core.config import global_settings
from newrelic.hooks.logger_logging import add_nr_linking_metadata


def _nr_log_forwarder(message_instance):
    transaction = current_transaction()
    record = message_instance.record
    message = record.get("_nr_original_message", record["message"])

    if transaction:
        settings = transaction.settings
    else:
        settings = global_settings()

    # Return early if application logging not enabled
    if settings and settings.application_logging and settings.application_logging.enabled:
        level = record["level"]
        level_name = "UNKNOWN" if not level else (level.name or "UNKNOWN")

        if settings.application_logging.metrics and settings.application_logging.metrics.enabled:
            if transaction:
                transaction.record_custom_metric("Logging/lines", {"count": 1})
                transaction.record_custom_metric("Logging/lines/%s" % level_name, {"count": 1})
            else:
                application = application_instance(activate=False)
                if application and application.enabled:
                    application.record_custom_metric("Logging/lines", {"count": 1})
                    application.record_custom_metric("Logging/lines/%s" % level_name, {"count": 1})
            
        if settings.application_logging.forwarding and settings.application_logging.forwarding.enabled:
            try:
                record_log_event(message, level_name, int(record["time"].timestamp()))
            except Exception:
                pass


@property
def patcher(self):
    original_patcher = getattr(self, "_nr_patcher", None)
    def _patcher(record):
        if original_patcher:
            record = original_patcher(record)
        
        transaction = current_transaction()

        if transaction:
            settings = transaction.settings
        else:
            settings = global_settings()

        if settings and settings.application_logging and settings.application_logging.enabled:
            if settings.application_logging.local_decorating and settings.application_logging.local_decorating.enabled:
                record["_nr_original_message"] = message = record["message"]
                record["message"] = add_nr_linking_metadata(message)

    return _patcher


@patcher.setter
def patcher(self, value):
    self._nr_patcher = value


def wrap_Logger_init(wrapped, instance, args, kwargs):
    logger = wrapped(*args, **kwargs)
    patch_loguru_logger(logger)
    return logger


def patch_loguru_logger(logger):
    if hasattr(logger, "_core") and not hasattr(logger._core, "_nr_instrumented"):
        core = logger._core
        logger.add(_nr_log_forwarder)
        original_patcher = core.patcher
        core.__class__.patcher = patcher
        core.patcher = original_patcher  # Add the original patcher back in using the setter
        logger._core._nr_instrumented = True


def instrument_loguru_logger(module):
    if hasattr(module, "Logger"):
        wrap_function_wrapper(module, "Logger.__init__", wrap_Logger_init)


def instrument_loguru(module):
    if hasattr(module, "logger"):
        if hasattr(module.logger, "_core") and not hasattr(module.logger._core, "_nr_instrumented"):
            patch_loguru_logger(module.logger)
