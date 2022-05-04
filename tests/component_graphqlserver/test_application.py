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
