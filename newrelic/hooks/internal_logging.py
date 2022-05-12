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
from newrelic.api.time_trace import get_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.core.config import global_settings

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

def is_null_handlers(handler):
    from logging.handlers import NullHandler


def bind_callHandlers(record):
    return record


def bind_emit(record):
    return record


def add_nr_linking_metadata(message):
    available_metadata = get_linking_metadata()
    entity_name = urlencode(available_metadata.get("entity.name", "")) 
    entity_guid = available_metadata.get("entity.guid", "") 
    span_id = available_metadata.get("span.id", "")
    trace_id = available_metadata.get("trace.id", "")
    hostname = available_metadata.get("hostname", "")

    nr_linking_str = "|".join(("NR-LINKING", entity_guid, hostname, trace_id, span_id, entity_name))
    return "%s %s|" % (message, nr_linking_str)

def wrap_emit(wrapped, instance, args, kwargs):
    return wrapped(*args, **kwargs)


def wrap_getMessage(wrapped, instance, args, kwargs):
    message = wrapped(*args, **kwargs)
    return add_nr_linking_metadata(message)


def wrap_callHandlers(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    record = bind_callHandlers(*args, **kwargs)

    logger_name = getattr(instance, "name", None)
    if logger_name and logger_name.split(".")[0] == "newrelic":
        return wrapped(*args, **kwargs)

    if transaction:
        settings = transaction.settings
    else:
        settings = global_settings()

    if settings and settings.application_logging and settings.application_logging.enabled and settings.application_logging.metrics.enabled:
        level_name = str(getattr(record, "levelname", "UNKNOWN"))
        if transaction:
            transaction.record_custom_metric("Logging/lines", {"count": 1})
            transaction.record_custom_metric("Logging/lines/%s" % level_name, {"count": 1})
        else:
            application = application_instance(activate=False)
            if application and application.enabled:
                application.record_custom_metric("Logging/lines", {"count": 1})
                application.record_custom_metric("Logging/lines/%s" % level_name, {"count": 1})
    
    if settings and settings.application_logging and settings.application_logging.enabled and settings.application_logging.local_decorating.enabled:
        record._nr_original_message = record.getMessage

    wrap_handlers(instance)

    return wrapped(*args, **kwargs)


def wrap_handlers(logger):
    handlers = logger.handlers
    for handler in handlers:
        # Check to see if handler has _nr_wrapper attr and if not, add it
#        value = getattr(handler, "_nr_wrapper", None)
#        if not value:
#            handler._nr_wrapper = handler.__wrapped__._nr_wrapper
        # breakpoint()
        pass

    # Recurse up parent tree
    if logger.propagate and logger.parent is not None:
        wrap_handlers(logger.parent)



def instrument_cpython_Lib_logging_init(module):
    if hasattr(module, "Logger"):
        if hasattr(module.Logger, "callHandlers"):
            wrap_function_wrapper(module, "Logger.callHandlers", wrap_callHandlers)

    if hasattr(module, "StreamHandler"):
        if hasattr(module.Logger, "emit"):
            wrap_function_wrapper(module, "StreamHandler.emit", wrap_emit)

    if hasattr(module, "Handler"):
        if hasattr(module.Logger, "emit"):
            wrap_function_wrapper(module, "StreamHandler.emit", wrap_emit)
