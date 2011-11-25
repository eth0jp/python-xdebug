import pyxdebug

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

if __name__ == '__main__':
    import nose
    nose.main()
