# Discovery and evaluation

## Research question

Can a creator or reviewer trace a commission discrepancy to a promotion link,
an order, a refund and a versioned offer? The public YouShop guides document
offers, creator links and payment events. They do not establish how often
disputes arise or which internal process causes them. See the [evidence
registry](provenance.md) for the scope of each observation.

In the simulated refund journey, an offer links a creator to a sale, the
payment is refunded, and a booked commission remains. A reviewer can check
three competing explanations: an omitted refund, a stale commission entry,
or an offer with different terms. The first needs ledger evidence, the
second needs a booked amount and the third needs the applicable contract.
In the legacy demo only ledger evidence exists. Its commission stays unknown.

## Comparison with public product documentation

- Hotmart documents tracking links that preserve attribution across offers.
  This motivates retaining the link with the offer and credited creator.
  [Hotmart tracking links](https://help.hotmart.com/pt-br/article/216441767/como-criar-links-de-divulgacao-hotlinks-alternativos-dinamicos-sendo-afiliado-)
- Kiwify documents a reserve to cover future refunds. An observed payment
  and an available balance can therefore answer different questions.
  [Kiwify reserves](https://ajuda.kiwify.com.br/pt-br/article/como-funciona-a-reserva-de-seguranca-do-saldo-frnn6u/)
- impact.com documents reversals, reasons and lookup by action identifier.
  This supports showing the evidence behind a reviewable case.
  [impact.com reversals](https://help.impact.com/partner/what-would-you-like-to-learn-about/platform-features/action-management/reversed-actions-explained-for-partners)

These comparisons inform product design. The prototype does not transfer
another platform's contract to YouShop. No interviews, operational loss
estimates or claims of market uniqueness are part of these findings.

### Additional comparisons

- Monetizze describes product-specific commission attribution models. A policy
  version therefore matters when explaining credit. [Monetizze attribution](https://help.monetizze.com.br/afiliacao/modelos-de-atribuicao-de-comissao)
- Eduzz exposes sales, fees, refunds, transfers and blocks in its account
  statement. A movement type gives a balance change context. [Eduzz statement](https://ajuda.eduzz.com/hc/pt-br/articles/4402964669467-extrato-financeiro-%C3%B3rbita)
- Shopee distinguishes paid orders in transit from completed orders undergoing
  commission validation. The example illustrates why delivery and payment
  evidence have different meanings. [Shopee affiliate reporting](https://help.shopee.com.br/portal/10/article/163052-Como-acompanhar-as-vendas-geradas-pelo-seu-link-de-afiliado)
- Stripe offers payout reconciliation reporting. A payout can be inspected
  through its component transactions. [Stripe payout reconciliation](https://docs.stripe.com/reports/payout-reconciliation)
- Shopify describes suggested changes prepared for merchant review. This
  informed the decision to make rule acceptance explicit. [Shopify Sidekick](https://help.shopify.com/en/manual/ai-powered-tools/sidekick/pulse)
- PartnerStack supports commission review with reasons visible to partners.
  An explanation and a decision can have separate authors. [PartnerStack review](https://support.partnerstack.com/hc/en-us/articles/360009840773-Reviewing-partner-commissions)
- Tipalti reports payment status and transaction references, which suggests
  preserving identifiers alongside financial totals. [Tipalti payment reports](https://help.tipalti.com/hc/en-us/articles/30607389186455-Payment-reports)

### Public feedback and causal limits

A public withdrawal and affiliate-listing complaint motivates testing whether
an operator can identify missing evidence. A consumer report is a
self-selected account. Its cause, frequency and outcome have not been
independently established. No identifying details or operational records from
the complaint were included in the fixtures. [Public consumer report](https://www.reclameaqui.com.br/youshop-tecnologia-servicos-e-pagamentos/nao-consigo-realizar-saque-e-nao-me-aceitam-na-vitrine-de-afiliados_JS8-g6vXrXPuxeIq/)

## Experimental interpretation

Each fixed scenario has a label assigned in source. The evaluator runs the
decision function on the event sequence, then compares its output to that
label. Review both the counts and individual cases at `/api/validation`.
The cases are designed regressions and are visible to the developer.
Independent evaluation requires held-out orders, unfamiliar questions and
a blinded reviewer. For a manual versus language-model comparison, provide
the same case and question to each evaluator, record elapsed time and score
amount accuracy, event citations, source support and abstention separately.
Human baseline times and production error rates remain unmeasured.

With the local model imported, run `python evaluation/compare.py` at the
project root. The script supplies four fixed event sequences and explicit
arithmetic instructions to the standalone model. It checks each method's net
amount and review flag against a hand-written answer key. Timings include
local HTTP and inference for the model path. They do not measure operator time.
