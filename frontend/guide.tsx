import React from "react";

export const areas = {
  "Visão geral": "Resumo da operação",
  TrustGraph: "Conferir pedido",
  Creator: "Comissões por criador",
  Simulação: "Testar cenários",
  Defesa: "Avaliar regras",
  Ajuda: "Guia do Sentinel",
};

const terms = [
  ["Criador (creator)", "Pessoa que divulga um produto. O link de divulgação permite associar a venda a quem a indicou."],
  ["Oferta e comissão", "A oferta reúne as condições da venda. No exemplo, a comissão corresponde a 10% do valor que sobra após os reembolsos."],
  ["Prevista e registrada", "Prevista é a comissão calculada pela regra da oferta. Registrada é a quantia lançada para o criador. Uma diferença pede conferência."],
  ["Conciliação", "Conferência entre pagamento, reembolso, comissão e atribuição. Conciliado significa que a regra em uso não encontrou divergência. Uma regra incompleta pode deixar um problema passar."],
  ["TrustGraph", "Nome do histórico que liga criador, link, oferta, pedido e valores. Abra cada etapa para consultar seu registro."],
  ["Alerta e revisão", "Um alerta é um pedido de conferência. Uma pessoa consulta as evidências e registra se confirma ou descarta o alerta."],
  ["VP, VN, FP e FN", "Verdadeiro positivo é um problema sinalizado. Verdadeiro negativo é um pedido regular liberado. Falso positivo é um alerta indevido. Falso negativo é um problema que passou sem alerta."],
  ["IA, AI e Ollama", "IA significa inteligência artificial (AI em inglês). Ollama executa o modelo local que seleciona evidências e cenários. O cálculo dos valores segue a regra da oferta."],
  ["API e ID", "API é o meio pelo qual o painel consulta o sistema. ID é o identificador que permite localizar exatamente um pedido ou evento."],
  ["Simulação e dados sintéticos", "Os pedidos são fictícios e têm resultados esperados conhecidos. Isso permite medir erros e testar mudanças sem movimentar dinheiro."],
];

export function Guide(){
  return <section><h1>Como funciona o Sentinel</h1><p>Uma marca define uma oferta, o criador divulga seu link e uma venda gera comissão. O Sentinel confere o que aconteceu depois.</p>
    <h2>Do pedido à decisão</h2><ol className="steps"><li><b>Confira a venda.</b> Compare o valor pago com os reembolsos e veja quem divulgou o produto.</li>
    <li><b>Compare as comissões.</b> Se a regra prevê R$ 0,00 e o registro contém R$ 10,00, abra as evidências e registre seu parecer.</li>
    <li><b>Teste a regra.</b> O simulador compara o resultado da conferência com a resposta esperada. Na avaliação, uma pessoa pode autorizar uma nova rodada com verificações adicionais.</li></ol>
    <h2>Termos que aparecem no painel</h2>{terms.map(([name,text])=><details key={name}><summary>{name}</summary><p>{text}</p></details>)}</section>
}

export function Example({open}:{open:()=>void}){
  return <article className="example"><div><small>Caso guiado · Reembolso integral</small><h2>R$ 10,00 de comissão após o reembolso</h2>
    <p>A venda de R$ 100,00 foi reembolsada por inteiro. A comissão prevista caiu para R$ 0,00, mas ficaram R$ 10,00 registrados.</p>
    <button onClick={open}>Conferir este pedido →</button></div>
    <dl className="receipt"><dt>Venda</dt><dd>R$ 100,00</dd><dt>Reembolso</dt><dd>− R$ 100,00</dd><dt>Comissão prevista</dt><dd>R$ 0,00</dd><dt>Comissão registrada</dt><dd>R$ 10,00</dd></dl></article>
}
