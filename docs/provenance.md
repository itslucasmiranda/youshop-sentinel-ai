# Data provenance

## Official public references reviewed on 2026-11-23

- **YS-CREATORS-01.** The guide describes brand approval for affiliations,
  promotion links and offer-level commission display. It supports vocabulary and
  does not establish an attribution algorithm or commission formula.
  [YouShop Creators app guide](https://ajuda.youshop.co/guides/IQ2WaPblIMMUqNhDSKdY)
- **YS-WEBHOOK-01.** The guide describes checkout and order payment events and
  provides instructions for testing a configured webhook. It informs the event
  vocabulary. The project has no verified payload contract or authorized sample.
  [YouShop webhook guide](https://ajuda.youshop.co/guides/1472b4bf-e3a3-485a-a396-2cd5c9ee9d95)
- **YS-TERMS-01.** The terms describe affiliate obligations and discuss payment
  disputes. This is context for future human review.
  [YouShop terms and policies](https://www.youshop.co/termosepoliticas)

## Synthetic data

`order-lifecycle-v1` is a hand-authored fixture with a payment and full refund
for one fictional order. Both rows have `origin=synthetic`. Identifiers,
timestamps, amounts and event keys are project-owned. Amounts are in integer
BRL centavos. The refund fixture models a financial lifecycle for testing.
It makes no assertion about how YouShop adjusts commissions.

To add an official reference, record its publisher, URL, access date, relevant
section, supported claim and limitations. Before promoting a claim to a rule,
record its supporting source, applicability, version and human approval.
Attribution precedence, payout timing, commission calculation and reversals
remain open pending evidence. The official challenge brief remains unverified.
