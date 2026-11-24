"""Fixed training contracts for fictional offers, reviewed as evidence only."""
from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class Journey:
    creator: str = "criador-demo"
    buyer: str = "comprador-demo"
    offer: str = "oferta-demo"
    product: str = "produto-demo"
    link: str = "link-demo"
    attributed_creator: str = "criador-demo"
    rate_bps: int = 1000
    posted_minor: int = 1000
    linked_creator_accounts: int = 1
    clicks: int = 12


BASE = Journey()
# Each fixture changes only the specified facts of a fictional order.
AFFILIATE_CASES = (
    ("comissao-normal", BASE, False),
    ("compra-propria", replace(BASE, buyer=BASE.creator), True),
    ("contas-associadas", replace(BASE, linked_creator_accounts=3), True),
    ("atribuicao-divergente", replace(BASE, attributed_creator="outro-demo"), True),
    ("trafego-atipico", replace(BASE, clicks=9000), True),
    ("comissao-apos-reembolso", BASE, True),
)


def affiliate_evidence(journey, net_minor):
    expected = max(net_minor, 0) * journey.rate_bps // 10000
    signals = [
        ("comprador_igual_ao_criador", journey.buyer == journey.creator),
        ("contas_associadas", journey.linked_creator_accounts > 1),
        ("atribuicao_divergente", journey.attributed_creator != journey.creator),
        ("trafego_atipico", journey.clicks > 5000),
        ("comissao_divergente", journey.posted_minor != expected),
    ]
    return dict(**asdict(journey), expected_minor=expected, rule="synthetic-offer-v1",
                reasons=[reason for reason, present in signals if present])
