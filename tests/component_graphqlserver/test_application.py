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

from framework_graphql.test_application import *
from framework_graphql.test_application import _graphql_base_rollup_metrics

from testing_support.fixtures import dt_enabled

EXTRA_SPANS = {
    "flask": 10,
    "sanic": 1,
}

@pytest.fixture(scope="session", params=["flask-sync", "sanic-sync", "sanic-async"])
def target_application(request):
    import graphql_server
    from _target_application import target_application
    target_application = target_application[request.param]

    version = graphql_server.__version__

    framework, schema_type = request.param.split("-")

    extra_spans = EXTRA_SPANS[framework]

    assert version is not None

    return "GraphQLServer", version, target_application, False, schema_type, extra_spans


@dt_enabled
def test_batch_query(target_application):
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application

    _test_first_query_scoped_metrics = [
        ("GraphQL/resolve/%s/hello" % framework, 1),
        ("GraphQL/operation/%s/query/first/hello" % framework, 1),
    ]
    _test_second_query_scoped_metrics = [
        ("GraphQL/resolve/%s/echo" % framework, 1),
        ("GraphQL/operation/%s/query/second/echo" % framework, 1),
    ]

    _expected_first_query_operation_attributes = {
        "graphql.operation.type": "query",
        "graphql.operation.name": "first",
    }
    _expected_first_query_resolver_attributes = {
        "graphql.field.name": "hello",
        "graphql.field.parentType": "Query",
        "graphql.field.path": "hello",
        "graphql.field.returnType": "String",
    }
    _expected_second_query_operation_attributes = {
        "graphql.operation.type": "query",
        "graphql.operation.name": "second",
    }
    _expected_second_query_resolver_attributes = {
        "graphql.field.name": "echo",
        "graphql.field.parentType": "Query",
        "graphql.field.path": "echo",
        "graphql.field.returnType": "String",
    }

    @validate_code_level_metrics("_target_schema_%s" % schema_type, "resolve_echo")
    @validate_code_level_metrics("_target_schema_%s" % schema_type, "resolve_hello")
    @validate_span_events(exact_agents=_expected_second_query_operation_attributes)
    @validate_span_events(exact_agents=_expected_second_query_resolver_attributes)
    @validate_span_events(exact_agents=_expected_first_query_operation_attributes)
    @validate_span_events(exact_agents=_expected_first_query_resolver_attributes)
    @validate_transaction_metrics(
        "query/second/echo",
        "GraphQL",
        scoped_metrics=_test_second_query_scoped_metrics + _test_first_query_scoped_metrics,
        rollup_metrics=_test_second_query_scoped_metrics + _test_first_query_scoped_metrics + _graphql_base_rollup_metrics(framework, version, is_bg, count=2),
        background_task=is_bg,
    )
    @conditional_decorator(background_task(), is_bg)
    def _test():
        response = target_application(['query first { hello }', ' query second { echo(echo: "test") }'])
        assert response[0]["data"]["hello"] == "Hello!"
        assert response[1]["data"]["echo"] == "test"

    _test()
