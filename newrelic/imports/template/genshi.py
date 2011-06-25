import types

from newrelic.agent import (wrap_object, transaction, FunctionTraceWrapper,
                            ObjectWrapper)

class stream_wrapper(ObjectWrapper):
    def __init__(self, stream, filepath):
        ObjectWrapper.__init__(self, stream)
        self.__filepath = filepath
    def __getattr__(self, name):
        if name == 'render':
            return FunctionTraceWrapper(getattr(self.__last_object__, name),
                    self.__filepath, 'Template/Render')
        return getattr(self.__last_object__, name)

class wrap_template(ObjectWrapper):
    def __call__(self, *args, **kwargs):
        current_transaction = transaction()
        if current_transaction:
            return stream_wrapper(self.__next__object__(*args, **kwargs),
                                  args[0].filepath)
        else:
            return self.__next__object__(*args, **kwargs)

def instrument(module):

    if module.__name__ == 'genshi.template.base':

        wrap_object(module, 'Template.generate', wrap_template)
