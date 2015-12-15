from __future__ import print_function

from llvmlite import ir

import rbc.exception as exc

from .astnode import ast_node, needs_builder, ASTNode
from .context import create_aligned_global, if_else
from .expression import LLVMPointerValue

def get_or_create_global(context, name):
    """Retrieve the LValue and llvm GlobalValue associated with an external
    variable with the specified name. If there is no defined external variable,
    a new uninitialised global variable is created which must be resolved at
    link time.

    """
    # Return the existing extern if present.
    if name in context.externals:
        return context.externals[name]

    # Create a new variable in the module and add it to the externals.
    value = create_aligned_global(context.module, context.word_type, name)
    value.modifiers = ['align {}'.format(context.bytes_per_word)]

    lvalue = LLVMPointerValue(value=value).dereference()
    context.externals[name] = lvalue
    return lvalue

# Statements
# ==========
#
# Statements, unlike rvalues or lvalues, do not return llvm Values when emitted.

@ast_node
class AutoStatement(ASTNode):
    """An auto variable is automatically allocated onto the stack."""
    @needs_builder
    def emit(self, context):
        val = context.builder.alloca(context.word_type, name=self.name)
        context.scope[self.name] = LLVMPointerValue(value=val).dereference()

@ast_node
class AutoVectorStatement(ASTNode):
    """An auto variable is automatically allocated onto the stack."""
    @needs_builder
    def emit(self, context):
        # Curiously, B uses the "maximum index" when declaring vectors. This
        # mean, for example, that "auto v[3]" should allocate storage for *4*
        # words on the stack rather than 3 as would seem more likely.
        vector_length = 1 + self.maxidx.value

        # Allocate values and record in scope
        val = context.builder.alloca(context.word_type, size=vector_length,
                                     name=self.name)

        # In contrast to non-vector auto variables, the "value" of a vecotr auto
        # is the actual underlying pointer rather than the dereferenced pointer.
        context.scope[self.name] = LLVMPointerValue(value=val)

@ast_node
class ExtrnStatement(ASTNode):
    def emit(self, context):
        context.scope[self.name] = get_or_create_global(context, self.name)

@ast_node
class MultipartStatement(ASTNode):
    """A statement which is like a CompoundStatement but there is no change of
    scope."""
    def emit(self, context):
        for statement in self.statements:
            statement.emit(context)

@ast_node
class CompoundStatement(MultipartStatement):
    """A group of statements emitted within a brand new scope. This isn't in any
    of the reference manuals I can find but it is C-like which suggests it may
    have been B-like.

    """
    def emit(self, context):
        with context.in_child_scope():
            MultipartStatement.emit(self, context)

@ast_node
class ReturnStatement(ASTNode):
    @needs_builder
    def emit(self, context):
        if self.return_value is None:
            # The default return value is 0
            ret_val = ir.Constant(context.word_type, 0)
        else:
            ret_val = self.return_value.emit(context)

        # Emit the return instruction
        context.builder.ret(ret_val)

        # A return instruction is a terminator and so we should create a new
        # block which any post-return instructions are appended to.
        new_block = context.builder.append_basic_block('post_return')
        context.builder.position_at_end(new_block)

@ast_node
class WhileStatement(ASTNode):
    @needs_builder
    def emit(self, context):
        # Create basic blocks for builder
        while_cond = context.builder.append_basic_block('while')
        while_body = context.builder.append_basic_block('whilethen')
        while_end = context.builder.append_basic_block('whileend')

        # Initially, branch into while loop condition test
        context.builder.branch(while_cond)

        # Position at start of condition block and emit condition and
        # test
        context.builder.position_at_end(while_cond)
        cond = self.cond.emit(context)
        zero = ir.Constant(context.word_type, 0)
        cond_is_not_zero = context.builder.icmp_signed('!=', cond, zero)

        # Conditionally branch to body or end of while
        context.builder.cbranch(cond_is_not_zero, while_body, while_end)

        # Position in body and emit
        context.builder.position_at_end(while_body)
        with context.setting_break_block(while_end):
            self.body.emit(context)

        # Branch back to condition
        context.builder.branch(while_cond)

        # Position after loop for further instructions
        context.builder.position_at_end(while_end)

@ast_node
class IfStatement(ASTNode):
    @needs_builder
    def emit(self, context):
        with if_else(context, self.cond) as (then, otherwise):
            with then:
                self.then.emit(context)
            with otherwise:
                if self.otherwise is not None:
                    self.otherwise.emit(context)

@ast_node
class ExpressionStatement(ASTNode):
    def emit(self, context):
        """An expression statement simply evaluates its expression and discards
        the result."""
        self.expression.emit(context)

@ast_node
class NullStatement(ASTNode):
    def emit(self, context):
        """A null statement does nothing."""

@ast_node
class LabelStatement(ASTNode):
    @needs_builder
    def emit(self, context):
        # Create a new basic block and record
        assert self.label not in context.labels
        new_block = context.builder.append_basic_block(self.label)
        context.labels[self.label] = new_block

        # Unconditionally branch to new block
        context.builder.branch(new_block)

        # Move context to new block
        context.builder.position_at_end(new_block)

        # Emit the following statement
        self.statement.emit(context)

@ast_node
class GotoStatement(ASTNode):
    """The goto statement becomes an unconditional branch. Since labels may be
    defined after the goto statement is emitted, the goto statement creates a
    new basic block for the branch to be appended to but does not immediately
    emit the branch instruction. Instead, a post-emit hook is added to emit the
    branch instruction once all labels have been defined.

    """
    def emit(self, context):
        current_block = context.builder.block
        current_builder = context.builder
        labels = context.labels

        # We create a post-emit hook so that the goto's label is resolved after
        # all the rest of the code is emitted.
        def hook(_):
            # Move back to the correct block
            current_builder.position_at_end(current_block)

            # Reset scope and retrieve block
            try:
                block = labels[self.label]
            except KeyError:
                raise exc.SemanticError('No such label: {}'.format(self.label))

            # Branch to label
            current_builder.branch(block)
        context.post_emit_hooks.append(hook)

        # Create a new block for appending future instructions
        new_block = context.builder.append_basic_block('post_goto')
        context.builder.position_at_end(new_block)

@ast_node
class BreakStatement(ASTNode):
    """The break statement is very much like a goto statement in that it turns
    into a conditional branch. Unlike a goto, the block to branch to is
    specified by the compound statement node when it is emitted. A break
    instruction branches to the basic block immediately after the current
    compound statement. If there is no compound statement being emitted, break
    is a no-op.

    """
    def emit(self, context):
        # Break statements are no-ops if we've no destination
        if context.break_block is None:
            return

        # Jump straight to the end of context
        context.builder.branch(context.break_block)

        # Add a new block for any following instructions
        new_block = context.builder.append_basic_block('post_break')
        context.builder.position_at_end(new_block)

@ast_node
class SwitchStatement(ASTNode):
    @needs_builder
    def emit(self, context):
        # Evaluate the switches condition value
        switch_val = self.rvalue.emit(context)

        # Add a block used to test condition
        test_block = context.builder.append_basic_block('switch_test')
        if not context.builder.block.is_terminated:
            context.builder.branch(test_block)

        # Create a new block for the switch
        switch_entry_block = context.builder.append_basic_block('switch_entry')
        end_block = context.builder.append_basic_block('switch_end')
        context.builder.position_at_end(switch_entry_block)

        # Emit the body with the switch context set
        with context.setting_switch_context(switch_val, test_block):
            with context.setting_break_block(end_block):
                self.body.emit(context)

            # Fall through to end block
            if not context.builder.block.is_terminated:
                context.builder.branch(end_block)

            # At the end of the test block, branch to end
            context.builder.position_at_end(context.switch_block)
            if not context.builder.block.is_terminated:
                context.builder.branch(end_block)

        # Set end block as new builder position
        context.builder.position_at_end(end_block)

@ast_node
class CaseStatement(ASTNode):
    @needs_builder
    def emit(self, context):
        if context.switch_val is None:
            raise exc.SemanticError('case outside of switch')

        # Create a new block for case
        case_block = context.builder.append_basic_block('case')
        if not context.builder.block.is_terminated:
            context.builder.branch(case_block)

        # Now move to test block
        context.builder.position_at_end(context.switch_block)

        if self.cond is None:
            # If there's no condition, then this is a default block
            context.builder.branch(case_block)
        elif not context.builder.block.is_terminated:
            # Test condition
            case_val = self.cond.emit(context)
            is_eq = context.builder.icmp_signed(
                '==', context.switch_val, case_val)
            next_block = context.builder.append_basic_block('case.else')
            context.builder.cbranch(is_eq, case_block, next_block)
            context.builder.position_at_end(next_block)
            context.switch_block = next_block

        # Emit next statements at end of case block
        context.builder.position_at_end(case_block)
        self.then.emit(context)

