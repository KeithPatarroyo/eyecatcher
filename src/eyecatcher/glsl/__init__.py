"""
GLSL pipeline: assemble receptor contributions into rendering rules.

RuleAssembler takes NetworkContribution(s) from NeatReceptor.compile() and
produces the full rule string. Genome → contribution is in representation.receptors.
"""

from .rule_assembler import RuleAssembler

__all__ = ["RuleAssembler"]
