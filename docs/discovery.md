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
