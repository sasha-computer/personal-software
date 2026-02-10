"""Shared typed aliases for domain search metadata and exports."""

from typing import Literal, TypedDict

DomainKind = Literal["exact", "hack"]
CheckMethod = Literal["DNS", "RDAP"]


class DomainMeta(TypedDict, total=False):
    type: DomainKind
    visual: str
    check_method: CheckMethod


type DomainMetaMap = dict[str, DomainMeta]
