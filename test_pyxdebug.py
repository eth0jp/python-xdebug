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


if __name__ == '__main__':
    import nose
    nose.main()
