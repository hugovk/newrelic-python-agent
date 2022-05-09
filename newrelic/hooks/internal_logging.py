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

from newrelic.api.time_trace import get_linking_metadata
from newrelic.common.object_wrapper import wrap_function_wrapper

def is_null_handlers(handler):
    from logging.handlers import NullHandler


def bind_callHandlers(record):
    return record


def bind_emit(record):
    return record


def add_nr_linking_metadata(message):
    available_metadata = get_linking_metadata()
    # entity_name = encoded(available_metadata["entity.name"]) if available_metadata["entity.name"] else " "
    # entity_guid = available_metadata["entity.guid"] if available_metadata["entity.guid"] else " "
    # span_id = available_metadata["span.id"] if available_metadata["span.id"] else " "
    # trace_id = available_metadata["trace.id"] if available_metadata["trace.id"] else " "
    # hostname = settings.host

    # nr_formatted_message = message + " NR-LINKING | " + entity_guid +  hostname + trace_id + span_id + entity_name
    # {entity.guid} | {hostname} | {trace.id} | {span.id} | {entity.name} |


def wrap_emit(wrapped, instance, args, kwargs):
    return wrapped(*args, **kwargs)


def wrap_callHandlers(wrapped, instance, args, kwargs):
    record = bind_callHandlers(*args, **kwargs)

    logger_name = getattr(instance, "name", None)
    if logger_name and logger_name.split(".")[0] == "newrelic":
        return wrapped(*args, **kwargs)

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
