"""Narrow user-directive Create decision for the text-only JARVIS pilot.

This is an executable, fail-closed *Core* policy, not an LLM grant.
It reads the original user utterance, never documents, model output,
or a recalled memory as authority. Unresolved scopes are NOT written.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from jarvis.memory.sensitive import looks_like_credential


_DIRECT = re.compile(
    r"^\s*(?:jarvis\s*[,!:\-]?\s+)?"
    r"(?:lembre(?:-se)?\s+(?:de\s+)?que|guarde\s+(?:na\s+mem[oó]ria\s+)?que|"
    r"memorize\s+que)\s+(.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)
_PROJECT = re.compile(r"\b(?:no|neste|nesse|para\s+o|do)\s+projeto\s+jarvis\b", re.I)
_OTHER_PROJECT = re.compile(r"\b(?:no|neste|nesse|para\s+o|do)\s+projeto\b", re.I)
_GENERAL = re.compile(
    r"\b(?:prefiro|prefer[eê]ncia\s+geral|minha\s+(?:cor|prefer[eê]ncia)\s+"
    r"(?:favorita|preferida)|em\s+geral)\b",
    re.I,
)
_TEMPORAL = re.compile(
    r"\b(?:amanh[aã]|lembrete|agende|agenda|notifique|avise|"
    r"pr[oó]xim[oa]|semana\s+que\s+vem|(?:[àa]s?)\s*\d{1,2}(?::\d\d)?)\b",
    re.I,
)
_COMPOUND = re.compile(
    r"\b(?:e\s+(?:esque[cç]a|apague|delete|envie|execute|compre|pague|"\n    r"transfira|publique|instale|exclua|mande)|"
    r"n[aã]o\s+(?:grave|guarde|registre|lembre))\b",
    re.I,
)
_INSTRUCTION = re.compile(
    r"\b(?:ignore\s+(?:as\s+)?instru[cç][oõ]es|"
    r"desative\s+(?:as\s+)?prote[cç][oõ]es|"
    r"contorne\s+(?:a\s+)?autoriza[cç][aã]o)\b",
    re.I,
)
_SENSITIVE = re.compile(
    r"\b(?:cpf|cnpj|rg|passaporte|endere[cç]o|cep|telefone|celular|"
    r"n[uú]mero\s+do\s+cart[aã]o|cart[aã]o\s+de\s+cr[eé]dito|"
    r"conta\s+banc[aá]ria|chave\s+pix|sal[aá]rio|"
    r"diagn[oó]stico|doen[cç]a|tratamento\s+m[eé]dico|"
    r"resultado\s+de\s+exame|prontu[aá]rio)\b",
    re.I,
)
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)


@dataclass(frozen=True)
class CreateDecision:
    result: str  # PERMITTED | CLARIFY | DENIED
    reason: str
    content: str | None = None
    scope: str | None = None


def evaluate_direct_create(utterance: str, *, classified_action: str) -> CreateDecision:
    """Require BOTH classification as Create AND a direct imperative in user text."""
    if classified_action != "memory_create":
        return CreateDecision("DENIED", "classifier_did_not_request_create")
    if not isinstance(utterance, str) or len(utterance) > 1024:
        return CreateDecision("DENIED", "invalid_utterance")
    match = _DIRECT.fullmatch(utterance)
    if match is None:
        return CreateDecision("DENIED", "not_an_explicit_directive")
    content = match.group(1).strip().rstrip(".! ").strip()
    if (not 6 <= len(content) <= 512 or "\n" in content or "\r" in content
            or "?" in utterance or ";" in content
            or _COMPOUND.search(content) or _INSTRUCTION.search(content)):
        return CreateDecision("DENIED", "complex_or_ambiguous_request")
    if _TEMPORAL.search(content):
        return CreateDecision("DENIED", "temporal_request_is_not_cognitive_memory")
    if (looks_like_credential(content) or _SENSITIVE.search(content)
            or _EMAIL.search(content)):
        return CreateDecision("DENIED", "sensitive_content_rejected")
    has_project = bool(_PROJECT.search(content))
    has_other_project = bool(_OTHER_PROJECT.search(content))
    has_general = bool(_GENERAL.search(content))
    if has_project and has_general and re.search(r"\bem\s+geral\b", content, re.I):
        return CreateDecision("CLARIFY", "conflicting_scope")
    if has_project:
        return CreateDecision("PERMITTED", "explicit_low_risk_project_create",
                              content, "project:jarvis")
    if has_other_project:
        return CreateDecision("CLARIFY", "project_not_identified")
    if re.search(r"\b(?:neste|nesse)\s+projeto\b", content, re.I):
        return CreateDecision("CLARIFY", "project_not_identified")
    if has_general:
        return CreateDecision("PERMITTED", "explicit_low_risk_global_create",
                              content, "global")
    return CreateDecision("CLARIFY", "scope_not_identified")
