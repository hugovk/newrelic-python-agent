import functools

from newrelic.api.transaction import Sentinel, Transaction
from newrelic.api.web_transaction import WebTransaction
from newrelic.common.encoding_utils import json_encode, obfuscate
from newrelic.core.config import finalize_application_settings


try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


def make_cross_agent_headers(payload, encoding_key, cat_id):
    value = obfuscate(json_encode(payload), encoding_key)
    id_value = obfuscate(cat_id, encoding_key)
    return {'X-NewRelic-Transaction': value, 'X-NewRelic-ID': id_value}


def make_synthetics_header(account_id, resource_id, job_id, monitor_id,
            encoding_key, version=1):
    value = [version, account_id, resource_id, job_id, monitor_id]
    value = obfuscate(json_encode(value), encoding_key)
    return {'X-NewRelic-Synthetics': value}


def make_incoming_headers(transaction):
    settings = transaction.settings
    encoding_key = settings.encoding_key

    headers = []

    cross_process_id = '1#2'
    path = 'test'
    queue_time = 1.0
    duration = 2.0
    read_length = 1024
    guid = '0123456789012345'
    record_tt = False

    payload = (cross_process_id, path, queue_time, duration, read_length,
            guid, record_tt)
    app_data = json_encode(payload)

    value = obfuscate(app_data, encoding_key)

    headers.append(('X-NewRelic-App-Data', value))

    return headers


class MockApplication(object):
    def __init__(self, name='Python Application', settings=None):
        settings = settings or {}
        final_settings = finalize_application_settings(settings)
        self.global_settings = final_settings
        self.global_settings.enabled = True
        self.settings = final_settings
        self.name = name
        self.active = True
        self.enabled = True
        self.thread_utilization = None
        self.attribute_filter = None
        self.nodes = []

    def activate(self):
        pass

    def normalize_name(self, name, rule_type):
        return name, False

    def record_transaction(self, data, *args):
        self.nodes.append(data)
        return None

    def compute_sampled(self, priority):
        return True


class MockTrace(object):
    def __init__(*args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        pass


class MockTransaction(WebTransaction):
    def __init__(self, application, *args, **kwargs):
        self._state = WebTransaction.STATE_STOPPED
        self.stopped = False
        self.enabled = True
        self.current_node = None
        self.client_cross_process_id = None
        self._frameworks = set()
        self._name_priority = 0
        self._settings = application.settings
        self._trace_node_count = 0
        self.current_node = Sentinel()
        self._string_cache = {}
        self._stack_trace_count = 0
        self._explain_plan_count = 0

        self.autorum_disabled = False
        self.rum_header_generated = False

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        pass

    def _push_current(self, *args, **kwargs):
        pass

    def _pop_current(self, *args, **kwargs):
        pass


class MockTransactionCache(object):
    def save_transaction(*args, **kwargs):
        pass

    def drop_transaction(*args, **kwargs):
        pass

    def current_thread_id(*args, **kwargs):
        pass


class MockTransactionCAT(MockTransaction):
    def __init__(self, *args, **kwargs):
        super(MockTransactionCAT, self).__init__(*args, **kwargs)
        self.client_cross_process_id = '1#1'
        self.queue_start = 0.0
        self.start_time = 0.0
        self.end_time = 0.0
        self._frozen_path = 'foobar'
        self._read_length = None
        self.guid = 'GUID'
        self.record_tt = False


class VeryMagicMock(MagicMock):
    def __setattr__(self, attrname, value):
        if attrname == '__init__':
            object.__setattr__(self, attrname, value)
        else:
            super(VeryMagicMock, self).__setattr__(attrname, value)


def TimeInstrumentBase(module):
    """
    Base class for benchmark suite for instrumentaiton points. Takes one
    argument, a module object, and returns a benchmark suite class. Will
    auto-discover instrumentation points by searching for methods in the module
    starting with `instrument_`.

    Example usage:
        from benchmarks.util import TimeInstrumentBase
        import newrelic.hooks.framework_django as framework_django

        class TimeDjangoInstrument(TimeInstrumentBase(framework_django)):
            pass
    """

    class _TimeInstrumentBase(object):
        params = []
        param_names = ['instrumentation point']

        def setup(self, param):
            self.function = getattr(self.module, param)

        def time_instrument(self, param):
            self.function(VeryMagicMock())

    for attribute in dir(module):
        if attribute.startswith('instrument_'):
            _TimeInstrumentBase.params.append(attribute)

    _TimeInstrumentBase.module = module
    return _TimeInstrumentBase


def _build_wrap_suites(bench_type, module, *spec_list):
    class _TimeWrapBase(object):
        """
        Base class for benchmark suite for hook points. Takes two arguments.
        The first is the a module object. The second is a list of "specs".
        Each spec has the form of: (name, [optional_params])
        optional_params is a dict with the following keys:

        extra_attr: list. default is []. sometimes the wrapping function
            will expect the instrance to have some other attributes, so
            figure out what they are and list them here. (we could
            finangle something with __getattr__ but that would incur
            overhead.)
        wrapped_params: int. default is 1. this is the number of params the
            wrapped function expects when called.
        returned_values: int. default is 1. sometimes the wrapper needs to call
            the wrapped function for some reason; this is the
            number of values it will return.
        returns_iterable: bool. default is False. set to True if this function
            yields a series of wrappers instead of just the wrapped function.

        Example usage:
            from benchmarks.util import TimeWrapBase, TimeWrappedBase
            import newrelic.hooks.framework_django as framework_django

            specs = [
                ('wrap_view_handler'),
                ('wrap_url_resolver_nnn', {
                    'extra_attr': ['name'],
                    'returned_values': 2
                }),
                # ...
            ]

            class TimeDjangoWrap(TimeWrapBase(framework_django, *specs)):
                pass

            class TimeDjangoWrapped(TimeWrappedBase(framework_django, *specs)):
                pass
        """

        param_names = [bench_type.title() + ' function']
        params = []
        spec_index = {}

        def setup(self, name):
            spec = self.spec_index[name]

            self.to_test = spec['to_test']

            self.dummy_args = [MagicMock()] * spec['wrapped_params']
            self.dummy_ret = ([MagicMock()] * spec['returned_values']
                              if spec['returned_values'] > 1 else MagicMock())

            self.wrapped_dummy = (self.wrap_dummy_iterable()
                                  if spec['returns_iterable']
                                  else self.wrap_dummy())

            if '__iter__' in dir(self.wrapped_dummy):
                self.wrapped_dummy = next(self.wrapped_dummy)

            self.transaction = Transaction(MockApplication())
            self.transaction.__enter__()

        def teardown(self, wrapped_name):
            self.transaction.__exit__(None, None, None)

        def dummy(self, *args, **kwargs):
            return self.dummy_ret

        def wrap_dummy(self):
            return self.to_test(self.dummy)

        def wrap_dummy_iterable(self):
            return self.to_test([self.dummy])

        def _time_wrap(self, wrapped_name):
            self.wrap_dummy()

        def _time_wrapped(self, wrapped_name):
            # call the wrapped function like this, so self won't bind
            (self.wrapped_dummy)(*self.dummy_args)

    defaults = {
        'extra_attr': [],
        'wrapped_params': 1,
        'returned_values': 1,
        'returns_iterable': False
    }

    timer = getattr(_TimeWrapBase, '_time_' + bench_type)
    for spec in spec_list:
        name, opts = (spec if isinstance(spec, tuple) else (spec, {}))

        _TimeWrapBase.params.append(name)
        _TimeWrapBase.spec_index[name] = defaults.copy()
        _TimeWrapBase.spec_index[name].update(opts)
        _TimeWrapBase.spec_index[name]['to_test'] = getattr(module, name)

        for extra_attr_name in _TimeWrapBase.spec_index[name]['extra_attr']:
            setattr(_TimeWrapBase, extra_attr_name, MagicMock())

    setattr(_TimeWrapBase, 'time_' + bench_type, timer)
    return _TimeWrapBase


TimeWrapBase = functools.partial(_build_wrap_suites, 'wrap')
TimeWrappedBase = functools.partial(_build_wrap_suites, 'wrapped')
