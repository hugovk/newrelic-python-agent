from sample_application_pb2 import Message
from sample_application_pb2_grpc import (
        SampleApplicationServicer as _SampleApplicationServicer)


class SampleApplicationServicer(_SampleApplicationServicer):

    def DoUnaryUnary(self, request, context):
        return Message(text='unary_unary: %s' % request.text)

    def DoUnaryStream(self, request, context):
        yield Message(text='unary_stream: %s' % request.text)

    def DoStreamUnary(self, request_iter, context):
        for request in request_iter:
            return Message(text='stream_unary: %s' % request.text)

    def DoStreamStream(self, request_iter, context):
        for request in request_iter:
            yield Message(text='stream_stream: %s' % request.text)

    def DoUnaryUnaryRaises(self, request, context):
        raise AssertionError('unary_unary: %s' % request.text)

    def DoUnaryStreamRaises(self, request, context):
        raise AssertionError('unary_stream: %s' % request.text)

    def DoStreamUnaryRaises(self, request_iter, context):
        for request in request_iter:
            raise AssertionError('stream_unary: %s' % request.text)

    def DoStreamStreamRaises(self, request_iter, context):
        for request in request_iter:
            raise AssertionError('stream_stream: %s' % request.text)
