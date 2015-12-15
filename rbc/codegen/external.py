from __future__ import print_function

from llvmlite import ir

from .astnode import ast_node, ASTNode

from .context import (
    address_to_llvm_ptr, create_constructor, create_aligned_global,
    mangle_symbol_name
)

from .expression import ConstantIntValue, LLVMPointerValue

# Globals
# =======
#
# Globals are emittables which have an additional "declare" method. All globals
# have their declare() method called before any emittables have emit() called.
# They should use this opportunity to register themselves with the current
# context.
#
# A global should expect the context's builder attribute to be None.

@ast_node
class SimpleDefinition(ASTNode):
    """An initialised external variable."""
    def __init__(self, **kwargs):
        ASTNode.__init__(self, **kwargs)
        self._lvalue = None

    def declare(self, context):
        # A simple global definition is represented in the llvm IR as a pointer
        # to the global value. Thus we may use a LLVMPointerValue to represent
        # the address of the lvalue.
        value = create_aligned_global(
            context.module, context.word_type, self.name)
        value.modifiers = ['align {}'.format(context.bytes_per_word)]

        # Set variable's initialiser. Don't bother with a constructor function
        # if the initialiser is a constant integer
        if self.init is not None and isinstance(self.init, ConstantIntValue):
            init_val = self.init.value
        else:
            init_val = 0
        value.initializer = ir.Constant(context.word_type, init_val)

        # Register this variable as an external symbol.
        self._lvalue = LLVMPointerValue(value=value).dereference()
        context.externals[self.name] = self._lvalue

    def emit(self, context):
        assert self._lvalue is not None

        # If we have no initialiser, we do not need to emit a constructor
        if self.init is None or isinstance(self.init, ConstantIntValue):
            return

        # Initialisers may themselves be global variables. In which case we need
        # to make sure we initialise them in the correct order.
        func = create_constructor(context, priority=0, name_hint=self.name)

        # Create entry block for function and associated builder
        block = func.append_basic_block(name='entry')

        # Assign the variable's value
        with context.new_function_body(block):
            init = self.init.emit(context)
            lvalue_address = self._lvalue.reference().emit(context)
            value_ptr = address_to_llvm_ptr(
                context, lvalue_address, context.word_type.as_pointer())
            context.builder.store(init, value_ptr)
            context.builder.ret_void()

@ast_node
class VectorDefinition(ASTNode):
    def __init__(self, **kwargs):
        ASTNode.__init__(self, **kwargs)
        self._lvalue = None

    def declare(self, context):
        # SCJ: "The actual size of the vector is the maximum of constant+1 and
        # the number of initial values. Any vector elements which are not
        # explicitly initialized have undefined values."
        if self.maxidx is not None:
            maxidx = self.maxidx.value
        else:
            maxidx = 0
        n_elems = max(len(self.ivals), maxidx + 1)

        # Initialise the value with zeros
        value_type = ir.ArrayType(context.word_type, n_elems)
        value = create_aligned_global(context.module, value_type, self.name)
        value.modifiers = ['align {}'.format(context.bytes_per_word)]
        value.initializer = ir.Constant(value_type, None)

        # Register this variable as an external symbol. Note that the pointer
        # value itself is registered unlike SimpleDefinition.
        self._lvalue = LLVMPointerValue(value=value)
        context.externals[self.name] = self._lvalue

    def emit(self, context):
        assert self._lvalue is not None
        if len(self.ivals) == 0:
            # No initialisation required
            return

        # Initialisers may themselves be global variables. In which case we need
        # to make sure we initialise them in the correct order.
        func = create_constructor(context, priority=0, name_hint=self.name)

        # Create entry block for function and associated builder
        block = func.append_basic_block(name='entry')

        # Assign the variable's values
        with context.new_function_body(block):
            lvalue = self._lvalue.emit(context)
            value_ptr = address_to_llvm_ptr(
                context, lvalue, context.word_type.as_pointer())
            for idx, val in enumerate(self.ivals):
                llvm_val = val.emit(context)
                idx_val = ir.Constant(context.word_type, idx)
                dest_ptr = context.builder.gep(value_ptr, [idx_val])
                context.builder.store(llvm_val, dest_ptr)
            context.builder.ret_void()

@ast_node
class FunctionDefinition(ASTNode):
    def __init__(self, **kwargs):
        ASTNode.__init__(self, **kwargs)
        self._func = None

    def declare(self, context):
        # Check we've not been declared already
        assert self._func is None

        # Create a new function type for this function
        word_type = context.word_type
        n_args = len(self.arg_names)
        func_type = ir.FunctionType(word_type, (word_type,) * n_args)

        # Create the function in the module and add to the global scope
        symbol_name = mangle_symbol_name(self.name)
        self._func = ir.Function(context.module, func_type, name=symbol_name)
        context.global_scope[self.name] = LLVMPointerValue(
            value=self._func).dereference()

    def emit(self, context):
        # Create entry block for function and associated builder
        block = self._func.append_basic_block(name='entry')
        with context.new_function_body(block):
            # Add function arguments to the function scope
            for arg_name, arg_value in zip(self.arg_names, self._func.args):
                arg_value.name = arg_name

                # Allocate stack variable for this argument and copy argument
                stack_var = context.builder.alloca(
                    context.word_type, name=arg_name)
                context.builder.store(arg_value, stack_var)

                # Store the stack variable in the scope
                context.scope[arg_name] = LLVMPointerValue(
                    value=stack_var).dereference()

            # Emit the function body
            self.body.emit(context)

            # All functions implicitly return 0 if there's no other return
            if not context.builder.block.is_terminated:
                context.builder.ret(ir.Constant(context.word_type, 0))
