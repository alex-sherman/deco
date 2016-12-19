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
    def __init__(self, concurrent_funcs):
        self.arguments = set()
        self.concurrent_funcs = concurrent_funcs
        self.encountered_funcs = set()

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

    @staticmethod
    def top_level_name(node):
        if type(node) is ast.Name:
            return node.id
        elif type(node) is ast.Subscript or type(node) is ast.Attribute:
            return SchedulerRewriter.top_level_name(node.value)
        return None

    def is_concurrent_call(self, node):
        return type(node) is ast.Call and type(node.func) is ast.Name and node.func.id in self.concurrent_funcs

    def is_valid_assignment(self, node):
        if not (type(node) is ast.Assign and self.is_concurrent_call(node.value)):
            return False
        if len(node.targets) != 1:
            raise ValueError("Concurrent assignment does not support multiple assignment targets")
        if not type(node.targets[0]) is ast.Subscript:
            raise ValueError("Concurrent assignment only valid for index based objects")
        return True

    def encounter_call(self, call):
        self.encountered_funcs.add(call.func.id)
        for arg in call.args:
            arg_name = SchedulerRewriter.top_level_name(arg)
            if arg_name is not None:
                self.arguments.add(arg_name)

    def generic_visit(self, node):
        node = NodeTransformer.generic_visit(self, node)
        if hasattr(node, 'body') and type(node.body) is list:
            returns = [i for i, child in enumerate(node.body) if type(child) is ast.Return]
            if len(returns) > 0:
                for wait in self.get_waits():
                    node.body.insert(returns[0], wait)
        return node

    def get_waits(self):
        return [ast.Expr(Call(ast.Attribute(ast.Name(fname, ast.Load()), 'wait', ast.Load()))) for fname in self.encountered_funcs]

    def visit_Call(self, node):
        node = self.generic_visit(node)
        if self.is_concurrent_call(node):
            self.encounter_call(node)
        elif any([self.is_concurrent_call(arg) for arg in node.args]):
            conc_args = [(i, arg) for i, arg in enumerate(node.args) if self.is_concurrent_call(arg)]
            if len(conc_args) > 1:
                raise Exception("Deco doesn't support functions with multiple @concurrent parameters")
            conc_call = conc_args[0][1]
            node.args[conc_args[0][0]] = ast.Name("__value__", ast.Load())
            call_lambda = ast.Lambda(ast.arguments(args = [ast.Name("__value__", ast.Param())], defaults = []), node)
            return copy_location(ast.Call(func = ast.Attribute(conc_call.func, 'call', ast.Load()),
                args = [call_lambda] + conc_call.args, keywords = []), node)
        return node

    def visit_Assign(self, node):
        if self.is_valid_assignment(node):
            call = node.value
            self.encounter_call(call)
            name = node.targets[0].value
            self.arguments.add(SchedulerRewriter.top_level_name(name))
            index = node.targets[0].slice.value
            call.func = ast.Attribute(call.func, 'assign', ast.Load())
            call.args = [ast.Tuple([name, index], ast.Load())] + call.args
            return copy_location(ast.Expr(call), node)
        return node

    def visit_FunctionDef(self, node):
        node.decorator_list = []
        node = self.generic_visit(node)
        node.body += self.get_waits()
        return node
