import pyxdebug

class TestPyXdebug(object):
    def __init__(self):
        self.xd = pyxdebug.PyXdebug()

    def test_initialize_default_value(self):
        assert getattr(self.xd, 'collect_imports', None)==1
        assert getattr(self.xd, 'collect_params', None)==0
        assert getattr(self.xd, 'collect_return', None)==0
        assert getattr(self.xd, 'collect_assignments', None)==0

    def test_initialize_debug_value(self):
        assert getattr(self.xd, 'start_time', False) is None
        assert getattr(self.xd, 'start_gmtime', False) is None
        assert getattr(self.xd, 'end_gmtime', False) is None
        assert getattr(self.xd, 'call_depth', None)==0
        assert getattr(self.xd, 'call_func_name', False) is None
        assert getattr(self.xd, 'late_dispatch', None)==[]
        assert getattr(self.xd, 'result', None)==[]

    def test_run_func(self):
        def func():
            a = 123
            b = 456
            c = a + b
        self.xd.run_func(func)
        

    def test_run_statement(self):
        locals_ = {}
        self.xd.run_statement("a = 123", locals_=locals_)
        assert locals_.get('a', None)==123

if __name__ == '__main__':
    import nose
    nose.main()
