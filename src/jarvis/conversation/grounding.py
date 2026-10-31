"""Answer grounding policy for desktop text conversations.

A prompt-based safeguard, not a deterministic factuality verifier.
Does not read Sofias Memory or authorize any operation.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol


class TextProvider(Protocol):
    def stream_text(self, *, model: str, messages: list[dict]) -> Iterator[str]: ...


_GROUNDING_POLICY = (
    "Responda usando apenas as informações disponíveis e distinga claramente "
    "a origem de cada afirmação quando isso for relevante. Mensagens anteriores "
    "do próprio assistente NÃO são prova de uma preferência ou de um fato "
    "declarado pelo usuário. Se a informação só apareceu numa resposta "
    "anterior do assistente, trate-a como afirmação anterior ainda não "
    "confirmada. Se houver dados recuperados do Sofias Memory, identifique-os "
    "como memória somente quando a consulta tiver resultado confirmado; "
    "não os confunda com uma declaração feita na conversa. "
    "Quando perguntarem como você chegou a uma resposta anterior, "
    "não invente motivos, consultas, palpites ou fontes. Caso a origem "
    "não esteja demonstrada pelo contexto disponível, admita a incerteza "
    "e proponha verificar a fonte apropriada. "
    "Se nenhum dado de memória foi recuperado neste turno, não afirme "
    "que consultou ou verificou o Sofias Memory."
)


class GroundedTextProvider:
    """Inject an ephemeral, trusted attribution policy; never persist it."""

    def __init__(self, provider: TextProvider):
        self.provider = provider

    def stream_text(self, *, model: str, messages: list[dict]) -> Iterator[str]:
        policy = {"role": "developer", "content": _GROUNDING_POLICY}
        yield from self.provider.stream_text(model=model, messages=[policy, *messages])
