# SPDX-FileCopyrightText: © 2023-2024 Devon D. Sparks 
# SPDX-License-Identifier: AGPL-3.0

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

