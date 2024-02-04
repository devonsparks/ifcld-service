from rdflib.parser import Parser
from rdflib.plugin import register


register(
    "step",
    Parser,
    "parsers.step.parser",
    "STEPParser",
)

register(
    "model/step",
    Parser,
    "parsers.step.parser",
    "STEPParser",
)

