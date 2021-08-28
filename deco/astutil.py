import ast
from ast import NodeTransformer, copy_location
import sys

def unindent(source_lines):
    for i, line in enumerate(source_lines):
        source_lines[i] = line.lstrip()
        if source_lines[i][:3] == "def":
            break

def Call(func, args=None, kwargs=None):
    if args is None:
        args = []
    if kwargs is None:
        kwargs = []
    if sys.version_info >= (3, 5):
        return ast.Call(func, args, kwargs)
    else:
        return ast.Call(func, args, kwargs, None, None)

class SchedulerRewriter(NodeTransformer):
    def __init__(self, concurrent_funcs, frameinfo):
        self.arguments = set()
        self.concurrent_funcs = concurrent_funcs
        self.encountered_funcs = set()
        self.line_offset = frameinfo.lineno - 1
        self.filename = frameinfo.filename

    def references_arg(self, node):
        if not isinstance(node, ast.AST):
            return False
        if type(node) is ast.Name:
            return type(node.ctx) is ast.Load and node.id in self.arguments
        for field in node._fields:
            if field == "body": continue
            value = getattr(node, field)
            if not hasattr(value, "__iter__"):
                value = [value]
            if any([self.references_arg(child) for child in value]):
                return True
        return False

    def not_implemented_error(self, node, message):
        return NotImplementedError(self.filename + "(" + str(node.lineno + self.line_offset) + ") " + message)

    @staticmethod
    def top_level_name(node):
        if type(node) is ast.Name:
            return node.id
        elif type(node) is ast.Subscript or type(node) is ast.Attribute:
            return SchedulerRewriter.top_level_name(node.value)
        return None

    def is_concurrent_call(self, node):
        return type(node) is ast.Call and type(node.func) is ast.Name and node.func.id in self.concurrent_funcs

    def encounter_call(self, call):
        self.encountered_funcs.add(call.func.id)
        for arg in call.args:
            arg_name = SchedulerRewriter.top_level_name(arg)
            if arg_name is not None:
                self.arguments.add(arg_name)

    def get_waits(self):
        return [ast.Expr(Call(ast.Attribute(ast.Name(fname, ast.Load()), 'wait', ast.Load()))) for fname in self.encountered_funcs]

    def visit_Call(self, node):
        if self.is_concurrent_call(node):
            raise self.not_implemented_error(node, "The usage of the @concurrent function is unsupported")
        node = self.generic_visit(node)
        return node

    def generic_visit(self, node):
        if (isinstance(node, ast.stmt) and self.references_arg(node)) or isinstance(node, ast.Return):
            return self.get_waits() + [node]
        return NodeTransformer.generic_visit(self, node)

    def makeCall(self, func, args = [], keywords = []):
        return ast.Call(func = func, args = args, keywords = keywords)

    def makeLambda(self, args, call):
        return ast.Lambda(ast.arguments(posonlyargs = [], args = args, defaults = [], kwonlyargs = [], kw_defaults = []), call)

    def visit_Expr(self, node):
        if type(node.value) is ast.Call:
            call = node.value
            if self.is_concurrent_call(call):
                self.encounter_call(call)
                return node
            elif any([self.is_concurrent_call(arg) for arg in call.args]):
                conc_args = [(i, arg) for i, arg in enumerate(call.args) if self.is_concurrent_call(arg)]
                if len(conc_args) > 1:
                    raise self.not_implemented_error(call, "Functions with multiple @concurrent parameters are unsupported")
                conc_call = conc_args[0][1]
                if isinstance(call.func, ast.Attribute):
                    self.arguments.add(SchedulerRewriter.top_level_name(call.func.value))
                self.encounter_call(conc_call)
                call.args[conc_args[0][0]] = ast.Name("__value__", ast.Load())
                if sys.version_info >= (3, 0):
                    args = [ast.arg("__value__", None)]
                else:
                    args = [ast.Name("__value__", ast.Param())]
                call_lambda = self.makeLambda(args, call)
                copy_location_kwargs = {
                    "func": ast.Attribute(conc_call.func, 'call', ast.Load()),
                    "args": [call_lambda] + conc_call.args,
                    "keywords": conc_call.keywords
                }
                if(sys.version_info < (3, 0)):
                    copy_location_kwargs["kwargs"] = conc_call.kwargs
                return copy_location(ast.Expr(ast.Call(**copy_location_kwargs)), node)
        return self.generic_visit(node)

    # List comprehensions are self contained, so no need to add to self.arguments
    def visit_ListComp(self, node):
        if self.is_concurrent_call(node.elt):
            self.encounter_call(node.elt)
            wrapper = self.makeCall(func = ast.Name('list', ast.Load()),
                args = [self.makeCall(func = ast.Name('map', ast.Load()),
                    args = [
                        self.makeLambda([ast.arg(arg='r')], self.makeCall(func = ast.Attribute(ast.Name('r', ast.Load()), 'result', ast.Load()))),
                        node
                    ])])
            return wrapper
        return self.generic_visit(node)

    def is_valid_assignment(self, node):
        if not (type(node) is ast.Assign and self.is_concurrent_call(node.value)):
            return False
        if len(node.targets) != 1:
            raise self.not_implemented_error(node, "Concurrent assignment does not support multiple assignment targets")
        if not type(node.targets[0]) is ast.Subscript:
            raise self.not_implemented_error(node, "Concurrent assignment only implemented for index based objects")
        return True

    def visit_Assign(self, node):
        if self.is_valid_assignment(node):
            call = node.value
            self.encounter_call(call)
            name = node.targets[0].value
            self.arguments.add(SchedulerRewriter.top_level_name(name))
            if hasattr(node.targets[0].slice, "value"):
                index = node.targets[0].slice.value
            else:
                index = node.targets[0].slice
            call.func = ast.Attribute(call.func, 'assign', ast.Load())
            call.args = [ast.Tuple([name, index], ast.Load())] + call.args
            return copy_location(ast.Expr(call), node)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.decorator_list = []
        node = self.generic_visit(node)
        node.body += self.get_waits()
        return node
