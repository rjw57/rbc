from __future__ import print_function

from llvmlite import ir

import rbc.exception as exc

from .astnode import ast_node, needs_builder, ASTNode
from .context import (
    address_to_llvm_ptr, llvm_ptr_to_address, create_aligned_global, if_else
)

def get_or_create_string_constant(context, string_bytes):
    """Return an llvm Value which points to a string constant with the
    specified bytes. A terminating *e is appended.

    """
    # Ensure string_bytes is a bytes object
    if not isinstance(string_bytes, bytes):
        string_bytes = bytes(string_bytes)

    # Try to look up string
    cached_ptr = context.string_constants.get(string_bytes)
    if cached_ptr is not None:
        return cached_ptr

    # We need to create one
    str_contents = bytearray(string_bytes)
    str_contents.append(4) # Terminating *e

    # We don't mangle the string constant name so that it won't collide with
    # any B symbols.
    str_name = '__str.{}'.format(len(context.string_constants))
    str_type = ir.ArrayType(ir.IntType(8), len(str_contents))
    str_ptr = create_aligned_global(
        context.module, str_type, context.module.get_unique_name(str_name))
    str_ptr.modifiers = ['align {}'.format(context.bytes_per_word)]

    # The string constant shouldn't be modified and merge it with any other
    # symbols with the same content. They're also local to the module.
    str_ptr.global_constant = True
    str_ptr.unnamed_addr = True
    str_ptr.linkage = 'private'

    # Initialise the variable with the terminated contents
    str_ptr.initializer = ir.Constant(str_type, str_contents)

    # Record the pointer and return
    context.string_constants[string_bytes] = (str_type, str_ptr)

    return str_ptr

# lvalues and rvalues
# ===================
#
# B divides values into two categories: lvalue and rvalue. The essential
# difference is that an lvalue represents the address in memory of some other
# value. Thus each lvalue has an associated rvalue (the value pointed to by the
# address) but each rvalue does not have an associated lvalue. If an rvalue
# *does* have some address associated with it the address may be obtained via
# the "&" or "reference" operator. This address is itself an rvalue. An rvalue
# may not be referenced. Both lvalues and rvalues may be "dereferenced" via the
# "*" operator to yield an lvalue.

class RValue(ASTNode):
    def dereference(self):
        """Return an LValue corresponding to the dereferencing of this value.
        The default implementation returns a DereferencedRValue instance.
        """
        return DereferencedRValue(rvalue=self)

    def reference(self):
        """An RValue cannot be referenced since it does not have an address."""
        raise exc.SemanticError('Cannot reference an rvalue.')

# Our implementation is such that that only lvalues are a dereferenced rvalue or
# an value retrieved from the current scope.

@ast_node
class DereferencedRValue(RValue):
    """A convenience wrapper representing a dereferenced RValue. The reference()
    method simply returns the dereferenced RValue. This value is an LValue in
    that it has a reference() method.

    """
    def reference(self):
        return self.rvalue

    @needs_builder
    def emit(self, context):
        # Convert the rvalue word address into a llvm pointer to a word
        ptr_type = context.word_type.as_pointer()
        rvalue_val = self.rvalue.emit(context)
        word_ptr = address_to_llvm_ptr(context, rvalue_val, ptr_type)

        # Load from pointer
        return context.builder.load(word_ptr)

@ast_node
class ScopeValue(RValue):
    """LValue constructed by dereferencing an address retrieved from the current
    scope."""
    def reference(self):
        return AddressOfScopeValue(name=self.name)

    def emit(self, context):
        try:
            val = context.scope[self.name]
        except KeyError:
            raise exc.SemanticError(
                'Variable not found in scope: {}'.format(self.name))
        return val.emit(context)

# In contrast there are many implementations of rvalues depending on how they're
# calculated.

@ast_node
class AddressOfScopeValue(RValue):
    """RValue corresponding to an address retrieved from the current scope."""
    def emit(self, context):
        try:
            val = context.scope[self.name]
        except KeyError:
            raise exc.SemanticError(
                'Variable not found in scope: {}'.format(self.name))
        return val.reference().emit(context)

@ast_node
class ReferencedLValue(RValue):
    def emit(self, context):
        return self.lvalue.reference().emit(context)

@ast_node
class ConditionalOpValue(RValue):
    @needs_builder
    def emit(self, context):
        with if_else(context, self.cond) as (then, otherwise):
            with then:
                then = self.then.emit(context)
                then_block = context.builder.block
            with otherwise:
                otherwise = self.otherwise.emit(context)
                otherwise_block = context.builder.block

        # We use a phi node to conditionally return the then or otherwise value
        # depending on which block was evaluated.
        value = context.builder.phi(context.word_type)
        value.add_incoming(then, then_block)
        value.add_incoming(otherwise, otherwise_block)
        return value

# Some binary ops map directly into LLVM instructions. They're noted in this
# mapping of operator to instruction name.
_SIMPLE_OPS = {
    '*': 'mul', '/': 'sdiv', '%': 'srem',
    '+': 'add', '-': 'sub',
    '<<': 'shl', '>>': 'lshr',
    '&': 'and_', '^': 'xor', '|': 'or_',
}

# Relational ops need their result casting up to a word. Due to the incredible
# dominance of C, B's successor, the relational operator names haven't changed
# and can be used directly in LLVM IR(!)
_REL_OPS = frozenset(['<', '<=', '>', '>=', '==', '!='])

# Helper functions for binary operators
def _emit_binary_op(context, lhs, op, rhs):
    # No short-cutting in B(!)
    lhs_val, rhs_val = lhs.emit(context), rhs.emit(context)

    if op in _SIMPLE_OPS:
        instr_name = _SIMPLE_OPS[op]
        return getattr(context.builder, instr_name)(lhs_val, rhs_val)

    if op in _REL_OPS:
        cmp_val = context.builder.icmp_signed(op, lhs_val, rhs_val)
        return context.builder.zext(cmp_val, context.word_type)

    raise exc.InternalCompilerError('Unknown binary op: {}'.format(op))

@ast_node
class BinaryOpValue(RValue):
    @needs_builder
    def emit(self, context):
        return _emit_binary_op(context, self.lhs, self.op, self.rhs)

@ast_node
class AssignmentOpValue(RValue):
    def emit(self, context):
        # In an assignment, the lhs is an lvalue and so has an address. Get the
        # address by referencing it and store the rhs to that address. Return
        # the rhs value.
        lhs_addr = self.lhs.reference().emit(context)
        ptr_type = context.word_type.as_pointer()
        lhs_ptr = address_to_llvm_ptr(context, lhs_addr, ptr_type)

        # If the op is anything other than '=', apply the given binary op
        # explicitly and rely on LLVM to perform any optimisation.
        if self.op != '=':
            rhs_val = _emit_binary_op(context, self.lhs, self.op[1:], self.rhs)
            context.builder.store(rhs_val, lhs_ptr)
        else:
            rhs_val = self.rhs.emit(context)
            context.builder.store(rhs_val, lhs_ptr)
        return rhs_val

@ast_node
class LeftUnaryOpValue(RValue):
    def reference(self):
        """The unary op '*' yields an LValue in that &*x is identically x."""
        if self.op != '*':
            return RValue.reference(self)
        return self.rhs

    @needs_builder
    def emit(self, context):
        if self.op == '&':
            return self.rhs.reference().emit(context)
        elif self.op == '*':
            return self.rhs.dereference().emit(context)
        elif self.op == '-':
            rhs = self.rhs.emit(context)
            return context.builder.neg(rhs)
        elif self.op == '~':
            rhs = self.rhs.emit(context)
            return context.builder.not_(rhs)
        elif self.op == '!':
            # Logical not
            rhs = self.rhs.emit(context)
            zero = ir.Constant(context.word_type, 0)
            is_zero = context.builder.icmp_unsigned('==', rhs, zero)
            return context.builder.zext(is_zero, context.word_type)
        elif self.op in ['++', '--']:
            # pre-{inc,dec}rement
            rhs = self.rhs.emit(context)
            rhs_addr_val = self.rhs.reference().emit(context)
            rhs_ptr = address_to_llvm_ptr(
                context, rhs_addr_val, context.word_type.as_pointer())
            one = ir.Constant(context.word_type, 1)
            if self.op == '++':
                val = context.builder.add(rhs, one)
            else:
                val = context.builder.sub(rhs, one)
            context.builder.store(val, rhs_ptr)
            return val

        raise exc.InternalCompilerError('Unknown unary op: {}'.format(self.op))

@ast_node
class RightUnaryOpValue(RValue):
    @needs_builder
    def emit(self, context):
        if self.op in ['++', '--']:
            # post-{inc,dec}rement
            lhs = self.lhs.emit(context)
            lhs_addr_val = self.lhs.reference().emit(context)
            lhs_ptr = address_to_llvm_ptr(
                context, lhs_addr_val, context.word_type.as_pointer())
            one = ir.Constant(context.word_type, 1)
            if self.op == '++':
                val = context.builder.add(lhs, one)
            else:
                val = context.builder.sub(lhs, one)
            context.builder.store(val, lhs_ptr)
            return lhs

        raise exc.InternalCompilerError('Unknown unary op: {}'.format(self.op))

@ast_node
class FunctionCallValue(RValue):
    @needs_builder
    def emit(self, context):
        # Emit function and args expressions to llvm Values
        func_addr_val = self.func.reference().emit(context)
        arg_vals = [arg.emit(context) for arg in self.args]

        # Convert function address into llvm function pointer
        func_type = ir.FunctionType(
            context.word_type, (context.word_type,) * len(arg_vals))
        func_ptr = address_to_llvm_ptr(
            context, func_addr_val, func_type.as_pointer())

        # Call function with arguments
        return context.builder.call(func_ptr, arg_vals)

@ast_node
class BuiltinValue(RValue):
    def emit(self, context):
        if self.name == '__bytes_per_word':
            return ir.Constant(context.word_type, context.bytes_per_word)

        raise exc.InternalCompilerError(
            'Unknown builtin value: {}'.format(self.name))

# Constants
# =========
#
# Constants are RValues whose word value is known at compile time. They share an
# attribute, "value", which is an Python object corresponding to the value of
# the node.

@ast_node
class ConstantIntValue(RValue):
    """An constant integer value."""
    def emit(self, context):
        return ir.Constant(context.word_type, self.value)

@ast_node
class StringConstantValue(RValue):
    @needs_builder
    def emit(self, context):
        # Get a pointer to the string
        str_ptr = get_or_create_string_constant(context, self.value)

        # Return the pointer as an address
        return llvm_ptr_to_address(context, str_ptr)

# Addresses
# =========
#
# LLVM addresses are byte-oriented but B addresses are word-oriented in that,
# given an lvalue "A", "*((&A)+1)" refers to the word which follows A in memory,
# not the word one byte into A. Other languages, such as C, have a type system
# to maintain this whereby each value is known to be either a pointer to a
# particular type or a non-pointer type. B's type system, such as it is, simply
# interprets a value as the type which it is used as. As such, "10[1]" is a
# valid B expression which is interpreted as the 11th word in memory. Addresses
# in B, therefore, are always word addresses.

class LLVMPointerValue(RValue):
    """An RValue corresponding to an llvm pointer type punned to the machine
    word type. The pointer value is divided by the machine word length in bytes
    to yield a value which is word-oriented.

    It is a Bad Idea (TM) to pass this AST node a pointer which is not
    word-aligned. There is no runtime check for alignment. So, "caveat caller".

    This class is not marked as an AST node and so cannot be constructed via the
    make_node() function. This reflects the fact that this is an "internal" node
    not intended for construction by the semantics.

    """
    @needs_builder
    def emit(self, context):
        return llvm_ptr_to_address(context, self.value)
