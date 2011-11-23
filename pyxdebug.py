# set encoding=utf-8

import sys
import os
import time
import inspect
import re
import linecache
from pprint import pformat
try:
    import resource
except ImportError:
    resource = None
import __builtin__


__version__ = '1.2.3'
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
        self.collect_assignments = 0

    def initialize(self):
        self.start_time = None
        self.start_gmtime = None
        self.end_gmtime = None
        self.call_depth = 0
        self.call_func_name = None
        self.late_dispatch = []
        self.result = []

    def run_func(self, func, *args, **kwds):
        self.initialize()
        self.call_func_name = getattr(func, '__name__', None)
        return self._run(func, *args, **kwds)

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
        original_trace = sys.gettrace()
        sys.settrace(self.trace_dispatch)

        # start time
        self.start_time = time.time()
        self.start_gmtime = time.gmtime()

        try:
            # call
            return func(*args, **kwds)
        finally:
            # reset profile hook
            sys.settrace(original_trace)

            # end time
            self.end_gmtime = time.gmtime()

            # reset import hook
            if import_hooked:
                __builtin__.__import__ = original_import
                __builtin__.reload = original_reload

            # finish
            trace = FinishTrace(None, 0)
            trace.setvalue(self.start_time)
            self.result.append(trace)

    def trace_dispatch(self, frame, event, arg):
        # ignore method
        if frame.f_code.co_name in ('__pyxdebug_import_hook', '__pyxdebug_reload_hook'):
            return

        # ignore frame
        if os.path.splitext(os.path.abspath(frame.f_back.f_code.co_filename))[0]==this_path:
            if self.call_func_name is None or self.call_func_name!=frame.f_code.co_name:
                return

        # normalize event
        if event[0:2]=='c_':
            event = event[2:]

        # wrap frame
        frame = FrameWrap(frame)
        frame.f_back = FrameWrap(frame.f_back)

        print "%-7s %-3d %s" % (event, frame.f_lineno, frame.get_line().rstrip())

        # dispatch call
        if event=='call':
            self.trace_call(frame, arg)

            # collect assignments
            if self.collect_assignments:
                self.late_dispatch.append(None)

        # dispatch return
        elif event=='return':
            # collect assignments
            if self.collect_assignments:
                self.trace_line(frame, arg)
                self.late_dispatch.pop()

            self.trace_return(frame, arg)

        # dispatch line
        elif event=='line':
            if self.collect_assignments:
                self.trace_line(frame, arg)

        return self.trace_dispatch

    def trace_call(self, frame, arg):
        trace = CallTrace(frame, self.call_depth)
        trace.setvalue(self.start_time, self.collect_params)
        self.result.append(trace)
        self.call_depth += 1

    def trace_return(self, frame, arg):
        self.call_depth -= 1
        if self.collect_return:
            trace = ReturnTrace(None, self.call_depth)
            trace.setvalue(arg)
            self.result.append(trace)

    def trace_line(self, frame, arg):
        back_frame = self.late_dispatch[self.call_depth-1]
        self.late_dispatch[self.call_depth-1] = frame

        if back_frame:
            frame = FrameWrap(frame)
            frame.set_position(back_frame)
            self._trace_line(frame, None)

    def _trace_line(self, frame, arg):
        line = frame.get_line().strip()
        match = re.compile(r"^([^\+\-\*/=]+)([\+\-\*/]?=[^=])(.+)$").match(line)
        if match:
            log = LogTrace(frame, self.call_depth)
            log.setvalue('%d execlate: %s' % (frame.f_lineno, frame.f_locals))
            #self.result.append(log)

            varnames = match.group(1).strip()
            try:
                varnames = re.compile(r"^\((.+)\)$").match(varnames).group(1).strip()
            except:
                pass 
            if re.compile(r"^(([a-zA-Z0-9_]+\.)?[a-zA-Z0-9_]+)(\s*,\s*(([a-zA-Z0-9_]+\.)?[a-zA-Z0-9_]+))*(\s*,\s*)?$").match(varnames):
                varnames = re.compile(r"\s*,\s*").split(varnames)
            else:
                varnames = None
            if varnames:
                for varname in varnames:
                    value = get_frame_var(frame, varname)
                    trace = SubstituteTrace(frame, self.call_depth)
                    trace.setvalue(varname, value)
                    self.result.append(trace)
        else:
            log = LogTrace(frame, self.call_depth)
            log.setvalue('nomatch: %s %s' % (line, frame.f_locals))
            #self.result.append(log)

    def trace_import(self, frame, arg):
        trace = ImportTrace(frame, self.call_depth)
        trace.setvalue(arg[0], arg[1], self.start_time)
        self.result.append(trace)
        self.call_depth += 1

    def trace_reload(self, frame, arg):
        trace = ReloadTrace(frame, self.call_depth)
        trace.setvalue(arg, self.start_time)
        self.result.append(trace)
        self.call_depth += 1

    def get_result(self):
        if self.end_gmtime is None:
            raise PyXdebugError('PyXdebug has not run yet')
        result = u"TRACE START [%s]\n" % (time.strftime('%Y-%m-%d %H:%M:%S', self.start_gmtime))
        result += u"\n".join([o.get_result() for o in self.result])
        result += u"\nTRACE END   [%s]\n\n" % (time.strftime('%Y-%m-%d %H:%M:%S', self.end_gmtime))
        return result


class AbstractTrace(object):
    def __init__(self, callee, call_depth):
        if callee:
            self.callee = callee
            self.caller = callee.f_back
        else:
            self.callee = None
            self.caller = None
        self.call_depth = call_depth


class CallTrace(AbstractTrace):
    def __init__(self, callee, call_depth):
        super(CallTrace, self).__init__(callee, call_depth)
        self.time = None
        self.collect_params = None
        self.memory = None

    def setvalue(self, start_time, collect_params=False):
        self.time = time.time() - start_time
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


class ReturnTrace(AbstractTrace):
    def setvalue(self, ret_value):
        self.ret_value = ret_value

    def get_result(self):
        sp = u' '*24 + u'  '*self.call_depth
        return u'%s>=> %s' % (sp, pformat(self.ret_value))


class SubstituteTrace(AbstractTrace):
    def __init__(self, callee, call_depth):
        super(SubstituteTrace, self).__init__(callee, call_depth)
        self.varname = None
        self.value = None

    def setvalue(self, varname, value):
        self.varname = varname
        self.value = value

    def get_result(self):
        sp = u' '*24 + u'  '*self.call_depth
        filename =  self.callee.f_code.co_filename
        lineno = self.callee.f_lineno
        return u'%s=> %s = %s %s:%d' % (sp, self.varname, pformat(self.value), filename, lineno)


class ImportTrace(CallTrace):
    def __init__(self, callee, call_depth):
        super(ImportTrace, self).__init__(callee, call_depth)
        self.name = None
        self.fromlist = None

    def setvalue(self, name, fromlist, start_time):
        super(ImportTrace, self).setvalue(start_time)
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


class ReloadTrace(CallTrace):
    def __init__(self, callee, call_depth):
        super(ReloadTrace, self).__init__(callee, call_depth)
        self.module = None

    def setvalue(self, module, start_time):
        super(ReloadTrace, self).setvalue(start_time)
        self.module = getattr(module, '__name__', None)

    def get_result(self):
        sp = u'  '*self.call_depth
        return u'%10.4f %10d   %s-> reload(%s) %s:%d' % (self.time or 0.0, self.memory or 0, sp, self.module, self.caller_filename(), self.caller_lineno())


class FinishTrace(CallTrace):
    def setvalue(self, start_time):
        super(FinishTrace, self).setvalue(start_time)

    def get_result(self):
        return u'%10.4f %10d' % (self.time or 0.0, self.memory or 0)


class LogTrace(AbstractTrace):
    def __init__(self, callee, call_depth):
        super(LogTrace, self).__init__(callee, call_depth)
        self.message = None

    def setvalue(self, message):
        self.message = message

    def get_result(self):
        sp = u' '*24 + u'  '*self.call_depth
        return u'%s*> %s' % (sp, self.message)


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


def get_frame_var(frame, varname):
    objectname = None
    attrname = None
    value = None
    try:
        objectname, attrname = varname.split('.')
    except:
        pass
    if objectname:
        object = frame.f_locals.get(objectname, None)
        value = getattr(object, attrname, None)
    else:
        value = frame.f_locals.get(varname, None)
    return value


def is_substitute(frame):
    line = frame.get_line().strip()
    if re.compile(r"^([^\+\-\*/=]+)([\+\-\*/]?=[^=])(.+)$").match(line):
        return True
    return False


def is_return(frame):
    line = frame.get_line().strip()
    words = re.compile(r"\s+").split(line)
    if len(words) and words[0]=='return':
        return True
    return False


class FrameWrap(object):
    def __init__(self, frame):
        keys = ('f_back', 'f_builtins', 'f_code', 'f_exc_traceback', 'f_exc_type', 'f_exc_value', 'f_globals', 'f_lasti', 'f_lineno', 'f_locals', 'f_restricted', 'f_trace')
        for key in keys:
            value = getattr(frame, key, None)
            setattr(self, key, value)

    def get_line(self):
        filename = self.f_code.co_filename
        lineno = self.f_lineno
        return linecache.getline(filename, lineno)

    def set_position(self, other):
        self.f_code = getattr(other, 'f_code', None)
        self.f_lineno = getattr(other, 'f_lineno', None)

    def is_equal_position(self, other):
        try:
            lineno1 = self.f_lineno
            filename1 = self.f_code.co_filename
            lineno2 = other.f_lineno
            filename2 = other.f_code.co_filename
            return lineno1==lineno2 and filename1==filename2
        except:
            return False


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

    # parser
    usage = 'pyxdebug.py [-o output_file_path] [-i collect_import] [-p collect_params] [-r collect_return] [-a collect_assignments] script_path [args ...]'
    parser = OptionParser(usage=usage)
    parser.allow_interspersed_args = False

    parser.add_option(
        '-o',
        '--outfile',
        action="callback",
        callback=action_output,
        dest="outfile",
        help="Save stats to <outfile>",
        default=sys.stdout
    )
    parser.add_option(
        '-i',
        '--collect_imports',
        action="callback",
        callback=action_int,
        dest="collect_imports",
        help="This setting, defaulting to 1, controls whether PyXdebug should write the filename used in import or reload to the trace files.",
        default=1
    )
    parser.add_option(
        '-p',
        '--collect_params',
        action="callback",
        callback=action_int,
        dest="collect_params",
        help="This setting, defaulting to 0, controls whether PyXdebug should collect the parameters passed to functions when a function call is recorded in either the function trace or the stack trace.",
        default=0
    )
    parser.add_option(
        '-r',
        '--collect_return',
        action="callback",
        callback=action_int,
        dest="collect_return",
        help="This setting, defaulting to 0, controls whether PyXdebug should write the return value of function calls to the trace files.",
        default=0
    )
    parser.add_option(
        '-a',
        '--collect_assignments',
        action="callback",
        callback=action_int,
        dest="collect_assignments",
        help="This setting, defaulting to 0, controls whether PyXdebug should add variable assignments to function traces.",
        default=0
    )

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
    xd.collect_assignments = options.collect_assignments
    xd.run_file(script_path)
    result = xd.get_result()

    # output
    options.outfile.write(result)


if __name__=='__main__':
    main()
