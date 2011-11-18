# set encoding=utf-8

import sys
import time
import inspect
import re
import logging
import traceback
import os
from pprint import pformat
try:
    import resource
except ImportError:
    resource = None
import __builtin__


__version__ = '1.0'
__author__ = 'Yoshida Tetsuya'
__license__ = 'MIT License'


this_path = __name__
if __name__=='__main__':
    this_path = __file__
this_path = os.path.splitext(os.path.abspath(this_path))[0]


class PyXdebug(object):
    def __init__(self):
        self.initialize()

        # collect options
        self.collect_imports = 1
        self.collect_params = 0
        self.collect_return = 0

    def initialize(self):
        self.start_time = None
        self.start_gmtime = None
        self.end_gmtime = None
        self.call_depth = 0
        self.call_func_name = None
        self.result = []

    def run_func(self, func, *args, **kwds):
        self.initialize()
        self.call_func_name = func.__name__
        self._run(func, *args, **kwds)

    def run_statement(self, statement):
        self.initialize()
        import __main__
        dict = __main__.__dict__
        def exec_statement():
            exec statement in dict, dict
        return self._run(exec_statement)

    def run_file(self, script_path, globals_=None):
        self.initialize()
        if globals_ is None:
            globals_ = globals()
        return self._run(execfile, script_path, globals_)

    def _run(self, func, *args, **kwds):
        if not hasattr(func, '__call__'):
            raise PyXdebugError('func is not callable')

        # import hook
        import_hooked = False
        if self.collect_imports:
            import_hooked = True
            original_import = __builtin__.__import__
            original_reload = __builtin__.reload

            def __pyxdebug_import_hook(name, globals=None, locals=None, fromlist=None):
                frame = inspect.currentframe()
                self.trace_import(frame, (name, fromlist))
                result = None
                try:
                    result = original_import(name, globals, locals, fromlist)
                    return result
                finally:
                    self.trace_return(frame, result)

            def __pyxdebug_reload_hook(module):
                frame = inspect.currentframe()
                self.trace_reload(frame, module)
                result = None
                try:
                    result = original_reload(module)
                    return result
                finally:
                    self.trace_return(frame, result)

            __builtin__.__import__ = __pyxdebug_import_hook
            __builtin__.reload = __pyxdebug_reload_hook

        # profile hook
        original_profile = sys.getprofile()
        sys.setprofile(self.trace_dispatch)

        # start time
        self.start_time = time.time()
        self.start_gmtime = time.gmtime()

        try:
            # call
            return func(*args, **kwds)
        finally:
            # reset profile hook
            sys.setprofile(original_profile)

            # end time
            self.end_gmtime = time.gmtime()

            # reset import hook
            if import_hooked:
                __builtin__.__import__ = original_import
                __builtin__.reload = original_reload

            # end
            trace = FinishTrace()
            trace.start(self.start_time)
            self.result.append(trace)

    def trace_dispatch(self, frame, event, arg):
        # ignore method
        if frame.f_code.co_name in ('__pyxdebug_import_hook', '__pyxdebug_reload_hook'):
            return

        # ignore frame
        if os.path.splitext(os.path.abspath(frame.f_back.f_code.co_filename))[0]==this_path:
            if self.call_func_name is None or self.call_func_name!=frame.f_code.co_name:
                return

        # dispatch
        if event=='call' or event=='c_call':
            self.trace_call(frame, arg)
        elif event=='return' or event=='c_return':
            self.trace_return(frame, arg)

    def trace_call(self, frame, arg):
        trace_index = len(self.result)
        trace = CallTrace()
        trace.start(frame, self.call_depth, self.start_time, self.collect_params)
        self.result.append(trace)
        self.call_depth += 1

    def trace_return(self, frame, arg):
        self.call_depth -= 1
        if self.collect_return:
            trace = ReturnTrace(arg, self.call_depth)
            self.result.append(trace)

    def trace_import(self, frame, arg):
        trace_index = len(self.result)
        trace = ImportTrace()
        trace.start(frame, arg[0], arg[1], self.call_depth, self.start_time)
        self.result.append(trace)
        self.call_depth += 1

    def trace_reload(self, frame, arg):
        trace = ReloadTrace(frame, arg, self.call_depth)
        self.call_depth += 1
        self.result.append(trace)

    def get_result(self):
        if self.end_gmtime is None:
            raise PyXdebugError('PyXdebug has not run yet')
        result = u"TRACE START [%s]\n" % (time.strftime('%Y-%m-%d %H:%M:%S', self.start_gmtime))
        result += u"\n".join([o.get_result() for o in self.result])
        result += u"\nTRACE END [%s]" % (time.strftime('%Y-%m-%d %H:%M:%S', self.end_gmtime))
        return result


class CallTrace(object):
    def __init__(self):
        self.time = None
        self.callee = None
        self.caller = None
        self.call_depth = None
        self.collect_params = None
        self.memory = None

    def start(self, frame, call_depth, start_time, collect_params=False):
        self.time = time.time() - start_time
        if frame:
            self.callee = frame
            self.caller = frame.f_back
        self.call_depth = call_depth
        self.collect_params = collect_params
        if resource is not None:
            self.memory = resource.getrusage(resource.RUSAGE_SELF).ru_minflt

    def callee_name(self):
        return get_method_name(self.callee)

    def caller_filename(self):
        return self.caller.f_code.co_filename

    def caller_lineno(self):
        return self.caller.f_lineno

    def get_params(self):
        params = []
        if self.collect_params:
            arginfo = inspect.getargvalues(self.callee)
            # args
            for key in arginfo.args:
                if isinstance(key, basestring):
                    params.append((key, arginfo.locals.get(key)))
                elif isinstance(key, list):
                    keys = key
                    for key in keys:
                        params.append((key, arginfo.locals.get(key)))
            # varargs
            if arginfo.varargs:
                for value in arginfo.locals[arginfo.varargs]:
                    params.append((None, value))
            # keywords
            if arginfo.keywords:
                kwds = arginfo.locals.get(arginfo.keywords)
                for key, value in kwds.iteritems():
                    params.append((key, value))
        return params

    def get_params_str(self):
        params_str = []
        params = self.get_params()
        for key, value in params:
            prefix = u''
            if key is not None:
                prefix = u'%s=' % key
            param_str = u'%s%s' % (prefix, pformat(value))
            params_str.append(param_str)
        return u', '.join(params_str)

    def get_result(self):
        sp = u'  '*self.call_depth
        params = self.get_params_str()
        return u'%10.4f %10d   %s-> %s(%s) %s:%d' % (self.time or 0.0, self.memory or 0, sp, self.callee_name(), params, self.caller_filename(), self.caller_lineno())


class ReturnTrace(object):
    def __init__(self, ret_value, call_depth):
        self.ret_value = ret_value
        self.call_depth = call_depth

    def get_result(self):
        sp = u'  '*self.call_depth
        return u'%s>=> %s' % (sp, pformat(self.ret_value))


class ImportTrace(CallTrace):
    def __init__(self):
        super(ImportTrace, self).__init__()
        self.name = None
        self.fromlist = None

    def start(self, frame, name, fromlist, call_depth, start_time):
        super(ImportTrace, self).start(frame, call_depth, start_time)
        self.name = name
        self.fromlist = fromlist

    def get_import_str(self):
        if self.fromlist:
            return u'from %s import %s' % (self.name, u', '.join(self.fromlist))
        else:
            return u'import %s' % (self.name,)

    def get_result(self):
        sp = u'  '*self.call_depth
        imp = self.get_import_str()
        return u'%10.4f %10d   %s-> %s %s:%d' % (self.time or 0.0, self.memory or 0, sp, imp, self.caller_filename(), self.caller_lineno())


class ReloadTrace(object):
    def __init__(self, frame, module, call_depth):
        self.frame = frame
        self.module = module
        self.call_depth = call_depth

    def get_result(self):
        sp = u' '*24 + u'  '*self.call_depth
        return u'%s-> reload(%s)' % (sp, self.module)


class FinishTrace(CallTrace):
    def start(self, start_time):
        super(FinishTrace, self).start(None, None, start_time)

    def get_result(self):
        return u'%10.4f %10d' % (self.time or 0.0, self.memory or 0)


class PyXdebugError(Exception):
    pass


def get_method_class(frame):
    arginfo = inspect.getargvalues(frame)

    obj = None
    if arginfo.args and len(arginfo.args):
        key = arginfo.args[0]
        if isinstance(key, (list, tuple)):
            return None
        obj = arginfo.locals.get(key)
    elif arginfo.varargs and len(arginfo.locals[arginfo.varargs]):
        obj = arginfo.locals[arginfo.varargs][0]
    elif arginfo.keywords:
        kwds = arginfo.locals.get(arginfo.keywords)
        if 'self' in kwds:
            obj = kwds['self']
        elif 'cls' in arginfo.keywords:
            obj = kwds['cls']

    if obj is not None:
        if not inspect.isclass(obj):
            obj = obj.__class__
        if not inspect.isclass(obj) or str(obj).startswith("<type '"):
            obj = None
        method = getattr(obj, frame.f_code.co_name, None)
        if not inspect.ismethod(method) and not inspect.isfunction(method):
            obj = None
    return obj


def get_method_name(frame):
    method_class = get_method_class(frame)
    classname = ''
    if method_class is not None:
        classname = str(method_class)
        try:
            classname = re.compile(r"<class '([^']+)'>").match(classname).group(1)
        except:
            pass
    if len(classname):
        methodname = classname + '.' + frame.f_code.co_name
    else:
        methodname = frame.f_code.co_name
    return methodname


#=================================================


def main():
    from optparse import OptionParser, OptionValueError

    # parser output option
    def action_output(option, opt_str, value, parser, *args, **kwargs):
        rargs = parser.rargs

        # next arg
        arg = rargs[0] if len(rargs) else '---'
        if (arg[:2] == "--" and len(arg) > 2) or (arg[:1] == "-" and len(arg) > 1 and arg[1] != "-"):
            raise OptionValueError('%s option requires an argument' % opt_str)

        del rargs[0]
        arg_l = arg.lower()
        if arg_l=='stdout':
            value = sys.stdout
        elif arg_l=='stderr':
            value = sys.stderr
        else:
            try:
                value = open(arg, 'a')
            except IOError, e:
                raise OptionValueError(str(e))
        setattr(parser.values, option.dest, value)

    def add_output_option(short, long, *args, **kwds):
        parser.add_option(short, long, action="callback", callback=action_output, *args, **kwds)

    # parser int option
    def action_int(option, opt_str, value, parser, *args, **kwargs):
        rargs = parser.rargs

        arg = rargs[0] if len(rargs) else '---'
        if (arg[:2] == "--" and len(arg) > 2) or (arg[:1] == "-" and len(arg) > 1 and arg[1] != "-"):
            raise OptionValueError('%s option requires an argument' % opt_str)

        value = arg
        del rargs[0]
        try:
            value = int(value)
        except:
            raise OptionValueError('%s option requires an integer value' % opt_str)
        setattr(parser.values, option.dest, value)

    def add_int_option(short, long, *args, **kwds):
        parser.add_option(short, long, action="callback", callback=action_int, *args, **kwds)

    # parser
    usage = 'pyxdebug.py [-o output_file_path] [-i collect_import] [-p collect_params] [-r collect_return] script_path [args ...]'
    parser = OptionParser(usage=usage)
    parser.allow_interspersed_args = False
    add_output_option('-o', '--outfile', dest="outfile", help="Save stats to <outfile>", default=sys.stdout)
    add_int_option('-i', '--collect_imports', dest="collect_imports", help="This setting, defaulting to 1, controls whether PyXdebug should write the filename used in import or reload to the trace files.", default=1)
    add_int_option('-p', '--collect_params', dest="collect_params", help="This setting, defaulting to 0, controls whether PyXdebug should collect the parameters passed to functions when a function call is recorded in either the function trace or the stack trace.", default=0)
    add_int_option('-r', '--collect_return', dest="collect_return", help="This setting, defaulting to 0, controls whether PyXdebug should write the return value of function calls to the trace files.", default=0)

    (options, args) = parser.parse_args()

    # script_path is this_path
    if len(args)==0 or os.path.splitext(os.path.abspath(args[0]))[0]==this_path:
        parser.print_help()
        sys.exit(2)

    # args
    script_path = args[0]
    sys.argv[:] = args

    # run
    xd = PyXdebug()
    xd.collect_imports = options.collect_imports
    xd.collect_params = options.collect_params
    xd.collect_return = options.collect_return
    xd.run_file(script_path)
    result = xd.get_result()

    # output
    options.outfile.write(result)


if __name__=='__main__':
    main()
