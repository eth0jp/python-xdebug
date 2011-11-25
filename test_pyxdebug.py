import pyxdebug
import inspect
import time


class TestPyXdebug(object):
    def test_initialize_default_value(self):
        xd = pyxdebug.PyXdebug()
        assert xd.collect_imports == 1
        assert xd.collect_params == 0
        assert xd.collect_return == 0
        assert xd.collect_assignments == 0

    def test_initialize_debug_value(self):
        xd = pyxdebug.PyXdebug()
        assert xd.start_time is None
        assert xd.start_gmtime is None
        assert xd.end_gmtime is None
        assert xd.call_depth == 0
        assert xd.call_func_name is None
        assert xd.late_dispatch == []
        assert xd.result == []

    def test_call_depth(self):
        xd = pyxdebug.PyXdebug()
        xd.run_file("example_run_file.py")
        result = [r for r in xd.result if r.__class__==pyxdebug.CallTrace and r.callee_name().endswith('.Fib.calc')]

        assert len(result)==15
        call_depth_arr = [0, 1, 2, 3, 4, 4, 3, 2, 3, 3, 1, 2, 3, 3, 2]
        for i in xrange(15):
            assert result[i].call_depth == call_depth_arr[i]

    def test_collect_imports(self):
        def func():
            import pyxdebug
            import pyxdebug
            import pyxdebug

        xd = pyxdebug.PyXdebug()
        xd.collect_import = 1
        xd.run_func(func)
        result = [r for r in xd.result if r.__class__==pyxdebug.ImportTrace]

        assert len(result)==3

    def test_collect_return(self):
        def func():
            return 123

        xd = pyxdebug.PyXdebug()
        xd.collect_return = 1
        xd.run_func(func)
        result = [r for r in xd.result if r.__class__==pyxdebug.ReturnTrace]

        assert len(result)==1
        assert result[0].value == 123

    def test_collect_assignments(self):
        def func():
            a = 123
            b = 456
            c = a + b

        xd = pyxdebug.PyXdebug()
        xd.collect_assignments = 1
        xd.run_func(func)
        result = [r for r in xd.result if r.__class__==pyxdebug.AssignmentTrace]

        assert len(result)==3
        assert result[0].varname == 'a'
        assert result[0].value == 123
        assert result[1].varname == 'b'
        assert result[1].value == 456
        assert result[2].varname == 'c'
        assert result[2].value == 123 + 456

    def test_run_statement(self):
        locals_ = {}
        xd = pyxdebug.PyXdebug()
        xd.run_statement("a = 123", locals_=locals_)
        assert locals_.get('a', None)==123


class TestCallTrace(object):
    def test_trace(self):
        trace = pyxdebug.CallTrace(inspect.currentframe(), 10)
        trace.setvalue(time.time(), 0)
        result = trace.get_result()

        assert result[24:24+20+2] == u'  '*10 + u'->'


class TestReturnTrace(object):
    def test_trace(self):
        trace = pyxdebug.ReturnTrace(inspect.currentframe(), 10)
        trace.setvalue(123)
        result = trace.get_result()

        assert result == u' '*24 + u'  '*10 + u'>=> 123'


class TestAssignmentTrace(object):
    def test_trace(self):
        trace = pyxdebug.AssignmentTrace(inspect.currentframe(), 10)
        trace.setvalue("var1", 123)
        result = trace.get_result()

        assert result[0:24+20+14] == u' '*24 + u'  '*10 + u'=> var1 = 123 '


class TestImportTrace(object):
    def test_trace_import(self):
        trace = pyxdebug.ImportTrace(inspect.currentframe(), 10)
        trace.setvalue("module1", None, time.time())
        result = trace.get_result()

        assert result[24:24+20+18] == u'  '*10 + u'-> import module1 '

    def test_trace_from(self):
        trace = pyxdebug.ImportTrace(inspect.currentframe(), 10)
        trace.setvalue("module1", ['*'], time.time())
        result = trace.get_result()

        assert result[24:24+20+25] == u'  '*10 + u'-> from module1 import * '

    def test_trace_from2(self):
        trace = pyxdebug.ImportTrace(inspect.currentframe(), 10)
        trace.setvalue("module1", ['cls1', 'cls2'], time.time())
        result = trace.get_result()

        assert result[24:24+20+34] == u'  '*10 + u'-> from module1 import cls1, cls2 '


class TestReloadTrace(object):
    def test_trace(self):
        trace = pyxdebug.ReloadTrace(inspect.currentframe(), 10)
        trace.setvalue(pyxdebug, time.time())
        result = trace.get_result()

        assert result[24:24+20+20] == u'  '*10 + u'-> reload(pyxdebug) '


class TestFinishTrace(object):
    def test_trace(self):
        trace = pyxdebug.FinishTrace(None, 0)
        trace.setvalue(time.time())
        result = trace.get_result()

        assert len(result) == 21
        assert result[10:11] == u' '


class TestFunction(object):
    def test_get_method_class(self):
        cls = pyxdebug.get_method_class(inspect.currentframe())
        assert cls == TestFunction

    def test_get_method_name(self):
        method_name = pyxdebug.get_method_name(inspect.currentframe())
        assert method_name.endswith('.TestFunction.test_get_method_name')

    def test_get_frame_var(self):
        value = pyxdebug.get_frame_var(inspect.currentframe(), 'self')
        assert value == self

        local_var = 123
        value = pyxdebug.get_frame_var(inspect.currentframe(), 'local_var')
        assert value == local_var


class TestFrameWrap(object):
    def test_wrap(self):
        frame = inspect.currentframe().f_back
        wrap = pyxdebug.FrameWrap(frame)

        assert frame.f_back == wrap.f_back
        assert frame.f_builtins == wrap.f_builtins
        assert frame.f_code == wrap.f_code
        assert frame.f_exc_traceback == wrap.f_exc_traceback
        assert frame.f_exc_type == wrap.f_exc_type
        assert frame.f_exc_value == wrap.f_exc_value
        assert frame.f_globals == wrap.f_globals
        assert frame.f_lasti == wrap.f_lasti
        assert frame.f_lineno == wrap.f_lineno
        assert frame.f_locals == wrap.f_locals
        assert frame.f_restricted == wrap.f_restricted
        assert frame.f_trace == wrap.f_trace

    def test_set_position(self):
        frame = inspect.currentframe()
        wrap = pyxdebug.FrameWrap(frame)
        wrap.set_position(frame.f_back)
        assert wrap.f_code == frame.f_back.f_code
        assert wrap.f_lineno == frame.f_back.f_lineno


if __name__ == '__main__':
    import nose
    nose.main()
