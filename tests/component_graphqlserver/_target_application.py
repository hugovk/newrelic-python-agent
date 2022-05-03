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

from flask import Flask
from sanic import Sanic
import json
import webtest

from testing_support.asgi_testing import AsgiTest
from framework_graphql._target_schema_sync import target_schema as target_schema_sync
from framework_graphql._target_schema_async import target_schema as target_schema_async
from graphql_server.flask import GraphQLView as FlaskView
from graphql_server.sanic import GraphQLView as SanicView


def set_middlware(middleware, view_middleware):
    view_middleware.clear()
    if middleware:
        try:
            view_middleware.extend(middleware)
        except TypeError:
            view_middleware.append(middleware)


sanic_names = ["GraphQLSync", "GraphQLAsync"]  # Not important but required


def sanic_execute(schema, is_async=False):
    sanic_app = Sanic(sanic_names.pop())
    sanic_middleware = []
    sanic_view = SanicView.as_view(schema=schema, middleware=sanic_middleware, enable_async=is_async)
    sanic_app.add_route(sanic_view, "/graphql")
    sanic_app = AsgiTest(sanic_app)

    def _sanic_execute(query, middleware=None):
        set_middlware(middleware, sanic_middleware)
        response = sanic_app.make_request(
            "POST", "/graphql", body=json.dumps({"query": query}), headers={"Content-Type": "application/json"}
        )
        body = json.loads(response.body.decode("utf-8"))

        if not isinstance(query, str) or "error" in query:
            try:
                assert response.status != 200, response
            except AssertionError:
                assert body["errors"], body
        else:
            assert response.status == 200
            assert "errors" not in body or not body["errors"], body

        return body["data"]

    return _sanic_execute


def flask_execute(schema):
    flask_app = Flask("FlaskGraphQL")
    flask_middleware = []
    flask_app.add_url_rule("/graphql", view_func=FlaskView.as_view("graphql", schema=schema, middleware=flask_middleware))
    flask_app = webtest.TestApp(flask_app)

    def _flask_execute(query, middleware=None):
        if not isinstance(query, str) or "error" in query:
            expect_errors = True
        else:
            expect_errors = False

        set_middlware(middleware, flask_middleware)
        response = flask_app.post(
            "/graphql",
            json.dumps({"query": query}),
            headers={"Content-Type": "application/json"},
            expect_errors=expect_errors,
        )

        body = json.loads(response.body.decode("utf-8"))
        if expect_errors:
            assert body["errors"], body
        else:
            assert "errors" not in body or not body["errors"], body

        return body["data"]

    return _flask_execute


target_application = {
    "flask-sync": flask_execute(target_schema_sync),
    "sanic-sync": sanic_execute(target_schema_sync),
    "sanic-async": sanic_execute(target_schema_async, True),
}
