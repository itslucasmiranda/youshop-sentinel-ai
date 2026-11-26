# YouShop Sentinel AI

Este protótipo ajuda um revisor a rastrear divergências de comissão. O exemplo principal acompanha uma venda fictícia de R$ 100,00, um reembolso integral e uma comissão de R$ 10,00 que continuou registrada. O painel usa dados sintéticos e guarda as decisões humanas em SQLite local.

## Abrir no Windows

Com Python 3.12 instalado, abra a pasta do repositório e execute no PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m sentinel.data
.\.venv\Scripts\python.exe -m uvicorn sentinel.main:app --host 127.0.0.1 --port 8001
```

Acesse [o painel local](http://127.0.0.1:8001/). Mantenha esse terminal aberto durante a demonstração. Para encerrar, pressione Ctrl+C. A carga dos dois eventos de exemplo pode ser repetida.

## Demonstração em três perguntas

No **Resumo da operação**, clique em **Conferir este pedido** para abrir o exemplo de comissão após reembolso. Se estiver em outro pedido, use **Abrir exemplo de comissão após reembolso**. Em **Perguntar sobre o pedido**, faça uma pergunta por vez. Use **Movimentações** para consultar o histórico e **Revisar alerta** para registrar um parecer.

1. **Por que a comissão ficou em revisão após o reembolso do pedido?** A regra da oferta prevê R$ 0,00 depois do reembolso integral. O registro mostra R$ 10,00. A diferença exige revisão humana.
2. **Qual evento comprova o reembolso deste pedido?** A evidência é o evento `lab-comissao-apos-reembolso-1`, no valor de R$ 100,00.
3. **Qual é a data do próximo saque?** O sistema informa que as evidências disponíveis são insuficientes.

A demonstração funciona com a conciliação local. Para experimentar a seleção de evidências por IA, mantenha o Ollama em execução com um modelo instalado, defina as variáveis abaixo e inicie novamente o servidor.

```powershell
$env:SENTINEL_LOCAL_AI = "1"
$env:SENTINEL_OLLAMA_MODEL = "sentinel-qwen-local"
```

O modelo compacto é o padrão. Para experimentar o outro modelo avaliado, use `qwen3:4b`. Os valores e os eventos vêm dos registros sintéticos. O formulário de revisão registra a decisão do operador.

## Verificar resultados

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m evaluation.retrieval
.\.venv\Scripts\python.exe -m evaluation.retrieval --live
```

A avaliação usa sete perguntas com respostas esperadas. A opção `--live` consulta os modelos disponíveis no Ollama local e registra as respostas, citações e tempos observados. Veja os [resultados desta entrega](evaluation/retrieval-v2.json), o [guia do operador](docs/trustgraph.md), a [pesquisa](docs/discovery.md), a [origem dos dados](docs/provenance.md) e o [roteiro do projeto](docs/delivery.md).

## Laboratório ampliado

Use o menu da central. O **Guia do Sentinel** explica as etapas de uma venda, as siglas e o papel da revisão humana. **Resumo da operação** resume 10.000 pedidos reproduzíveis, 500 creators e 100 produtos ao longo de 90 dias fictícios. Um pedido pode conter mais de um evento. **Testar cenários** monta uma bateria com controle regular e combinações autorizadas de reembolso, confirmação ausente e oferta vencida. O Ollama pode selecionar os casos. Com a IA desligada, o planejador prioriza lacunas observadas no controle inicial. Cada resultado abre o pedido em **Conferir pedido**, onde os nós revelam valores e identificadores.

Em **Avaliar regras**, o sistema mede quais verificações adicionais recuperam casos perdidos em 25 pedidos. Um revisor identificado pode aprovar a repetição em outros 25 pedidos ou rejeitar a proposta. Essas amostras seguem as mesmas regras sintéticas. O parecer fica salvo no SQLite. **Comissões por criador** apresenta 20 pedidos por perfil fictício com valores previstos e registrados. O seletor de perfis serve à demonstração local, sem autenticação de usuários reais.

Para o experimento de oferta vencida, a validade sintética termina na véspera da venda; nos outros casos ela termina 30 dias depois. Os números da carteira refletem a distribuição planejada dos cenários.
