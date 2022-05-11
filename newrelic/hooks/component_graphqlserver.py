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

import sys
from inspect import isawaitable

from newrelic.api.error_trace import ErrorTrace
from newrelic.api.graphql_trace import GraphQLOperationTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.core.graphql_utils import graphql_statement
from newrelic.hooks.framework_graphql import (
    framework_version as graphql_framework_version,
)
from newrelic.hooks.framework_graphql import ignore_graphql_duplicate_exception
from newrelic.hooks.framework_graphql_py3 import nr_coro_graphql_impl_wrapper


def framework_details():
    import graphql_server
    return ("GraphQLServer", getattr(graphql_server, "__version__", None))

def bind_get_response(schema, params, *args, **kwargs):
    return schema, getattr(params, "query", None)


def wrap_get_response(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    try:
        schema, query = bind_get_response(*args, **kwargs)
    except TypeError:
        return wrapped(*args, **kwargs)

    framework = framework_details()
    transaction.add_framework_info(name=framework[0], version=framework[1])
    transaction.add_framework_info(name="GraphQL", version=graphql_framework_version())

    if hasattr(query, "body"):
        query = query.body

    transaction.set_transaction_name(callable_name(wrapped), "GraphQL", priority=10)

    trace = GraphQLOperationTrace()
    trace.product = "GraphQLServer"
    trace.statement = graphql_statement(query)

    # Handle Schemas created from frameworks
    if hasattr(schema, "_nr_framework"):
        framework = schema._nr_framework
        trace.product = framework[0]
        transaction.add_framework_info(name=framework[0], version=framework[1])

    # Trace must be manually started and stopped to ensure it exists prior to and during the entire duration of the query.
    # Otherwise subsequent instrumentation will not be able to find an operation trace and will have issues.
    trace.__enter__()
    try:
        with ErrorTrace(ignore=ignore_graphql_duplicate_exception):
            result = wrapped(*args, **kwargs)
    except Exception as e:
        # Execution finished synchronously, exit immediately.
        trace.__exit__(*sys.exc_info())
        raise
    else:
        if isawaitable(result):
            # Asynchronous implementations
            # Return a coroutine that handles closing the operation trace
            return nr_coro_graphql_impl_wrapper(wrapped, trace, ignore_graphql_duplicate_exception, result)
        else:
            # Execution finished synchronously, exit immediately.
            trace.__exit__(None, None, None)
            return result


def instrument_graphqlserver(module):
    wrap_function_wrapper(module, "get_response", wrap_get_response)    
