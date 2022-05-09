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

from collections import namedtuple

from newrelic.core.metric import TimeMetric
from newrelic.packages import six


LogEventNode = namedtuple('LogEventNode', ['timestamp', 'level', 'message', 'attributes'])


# class LogEventNode(_LogEventNode):
#     def __init__(timestamp, level, message, attributes=None)
#     _common_attribute_keys = frozenset("entity.name", "entity.guid", "hostname")

#     @property
#     def common_attributes(self):
#         if self._common_attributes is None:
#             self._common_attributes, self._other_attributes = split_attributes()

#         return self._common_attributes

#     def split_attributes(self):
#         self._common_attributes = dict()
#         self._other_attributes = dict()

#         for k, v in six.iteritems(self.attributes):
#             if v is not None:
#                 if k in self._common_attribute_keys:
#                     self._common_attributes[key] = value
#                 else:
#                     self._other_attributes[key] = value


#     def time_metrics(self, stats, root, parent):
#         """Return a generator yielding the timed metrics for this log node"""

#         total_log_lines_metric_name = 'Logging/lines'

#         severity_log_lines_metric_name = 'Logging/lines/%s' % self.log_level

#         if application_logging.enabled and application_logging.metrics.enabled:
#             yield TimeMetric(name=total_log_lines_metric_name, scope="",
#                     duration=0.0, exclusive=None)

#             yield TimeMetric(name=severity_log_lines_metric_name, scope="",
#                          duration=0.0, exclusive=None)
