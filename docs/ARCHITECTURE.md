# Arquitetura — GeoResistivity (Fase 3)

- **Status:** aprovada em 2026-10-22 (D-5 a D-9)
- **Data:** 2026-10-22
- **Base:** versão `0.2.0` (branch `phase-2/hardening`)
- **Escopo:** levar o GeoResistivity de calculadora de sessão a software de campo e escritório
  para eletrorresistividade, começando pelas funcionalidades P1 do plano.

---

## 1. Objetivos

O software precisa:

1. funcionar **no campo**, muitas vezes sem internet, com entrada rápida e sem perda de dados;
2. funcionar **no escritório**, para revisar, corrigir, exportar e documentar;
3. manter a **correção científica** e a **rastreabilidade** que já existem: valores originais,
   unidades, conversão explícita e premissas declaradas;
4. continuar **testável sem interface**: o núcleo científico não pode depender da tecnologia
   de tela escolhida.

Funcionalidades P1 (do plano da Fase 3):

| # | Funcionalidade | Achados da auditoria |
| --- | --- | --- |
| P1.1 | Cálculo de K pela geometria (fórmula geral e arranjos) | C-05, C-08 |
| P1.2 | Leituras repetidas por estação (stacking) com controle de qualidade | C-07 |
| P1.3 | Levantamento persistente com metadados, arquivo de projeto e autosave | U-03, C-05 |
| P1.4 | Importação de CSV com pré-visualização e relatório de erros | — |
| P1.5 | Interface bilíngue PT-BR / EN | U-05 |

### 1.1 Referência real: a folha de campo SEV Schlumberger

Esta seção é baseada na folha impressa usada hoje em campo, "Sondagem Elétrica Vertical –
Arranjo Schlumberger", enviada pelo autor. Ela mostra o fluxo de trabalho que o software
precisa reproduzir:

- **Cabeçalho:** Área, Local, SEV nº, Data, Operador e **Azimute** da linha AB.
- **Programação fixa de espaçamentos:** AB/2 = 1,0 · 1,3 · 1,8 · 2,4 · 3,2 · 4,2 · 5,5 · 7,5 ·
  10 · 13 · 18 · 24 · 32 · 42 · 55 · 75 · 100 · 130 · 180 · 240 · 320 m, aproximadamente
  equiespaçados em escala logarítmica.
- **Tabela de K pré-calculada** por AB/2 e por **MN (comprimento total)** = 0,5 · 2 · 5 · 20 ·
  50 · 100 m. Cada MN cobre uma faixa de AB/2, e as faixas **se sobrepõem** em 2 a 4 linhas
  (por exemplo, AB/2 = 18 e 24 m têm K para MN = 0,5, 2 e 5 m). São os segmentos de
  superposição do item C-06.
- **Entrada por linha:** o operador anota ΔV e I e calcula ρa. O segundo par de colunas
  ΔV/I à direita é a **leitura de superposição** com o próximo MN no mesmo AB/2 (D-9).
- **Códigos por linha** (VN, VD, AM, AZ, VM…) ao lado de AB/2: as **cores de marcação no
  cabo/carretel** de cada posição de AB/2 (D-9).
- **Papel bilog** para plotar ρa (Ω·m) × AB/2 (m) em escala log-log fixa, com AB/2 de 1 a
  1000 m e ρa de 1 a 10 000 Ω·m.

**Conferência da tabela de K:** os 45 valores da folha batem com a fórmula exata de
Schlumberger `K = π·(L² − l²)/(2l)`, com L = AB/2 e **l = MN/2**. A maior diferença é 0,06%
(10,22 na folha contra 10,226 pela fórmula em AB/2 = 1,3 m, um truncamento em vez de
arredondamento). A tabela de K (só as constantes, nenhuma leitura de campo) vira um teste de
regressão no M2. **As leituras manuscritas da foto não serão copiadas para o repositório.**

**O que muda na proposta por causa da folha:**
1. A entrada principal passa a ser uma **folha de campo digital**: uma tabela com a
   programação AB/2 × MN já preenchida e o K calculado, em que o operador só digita ΔV e I, e
   ρa aparece na hora. O formulário de uma medição por vez continua existindo para medições
   avulsas.
2. A curva aparece **ao vivo** no mesmo formato do papel bilog (décadas fixas), com um
   segmento por MN. Antes isso era P2; uma versão básica entra na P1.
3. O software usa **MN total**, como a folha, e não MN/2. A conversão l = MN/2 fica só dentro
   da fórmula, documentada, para evitar erro de fator 2 na digitação.
4. Os metadados incluem **SEV nº** e **Azimute**.
5. O alerta de MN grande para Schlumberger foi recalibrado (seção 7.1): a própria folha usa
   L/l = 4,0 na primeira linha.

---

## 2. Restrições encontradas

| Restrição | Origem | Consequência |
| --- | --- | --- |
| O Streamlit precisa de um processo Python servindo a página. | Arquitetura do Streamlit | Em celular ou tablet sozinho não roda, a menos que o Python rode no navegador (stlite) ou o app seja hospedado. |
| O `st.text_input` não aceita `inputmode`. | Verificado no DOM na Fase 1 (U-04) | No celular, os campos numéricos abrem o teclado de letras. O `st.number_input` abriria o teclado numérico, mas a vírgula decimal ficaria a cargo do navegador e perderíamos a regra de ambiguidade (V-01). |
| O estado do Streamlit vive na sessão. | U-03 | A persistência precisa ser explícita: arquivo, autosave ou banco. |
| Muitas vezes não há internet no campo. | Uso real | Uma opção só online não serve como única forma de uso em campo. |
| Um único mantenedor. | Projeto pessoal e acadêmico | Duas bases de código (por exemplo, núcleo em Python e outro em JavaScript) teriam custo de manutenção alto e risco de divergência científica. |

---

## 3. Opções de execução

Esta é a decisão que mais muda o resto da arquitetura (D-5).

| Opção | Como funciona | Campo sem internet | Celular / tablet | Teclado numérico | Esforço | Risco |
| --- | --- | --- | --- | --- | --- | --- |
| **A. Streamlit local** | O app roda no notebook (`georesistivity app`). Um tablet ou celular pode abrir o app pelo Wi-Fi do notebook (hotspot), sem internet. | Sim | Sim, se houver notebook por perto | Não | Baixo | Baixo |
| **B. Streamlit hospedado** | O app fica em um servidor (Streamlit Community Cloud ou próprio) e é aberto pelo navegador. | Não | Sim | Não | Baixo | Médio: os dados passam por terceiros e a sessão continua volátil |
| **C. stlite (PWA)** | O mesmo app Streamlit roda inteiro no navegador via Pyodide/WebAssembly e pode ser instalado como aplicativo. Os arquivos ficam no IndexedDB do aparelho. | Sim, depois do primeiro carregamento | Sim, sozinho | Não | Médio | Médio-alto: o primeiro carregamento é pesado (Python, pandas e Matplotlib no navegador) e a versão do Streamlit embutida precisa ser validada (usamos recursos da 1.62+) |
| **D. Desktop nativo (Qt/PySide6)** | Interface de desktop nova, reutilizando o núcleo. | Sim | Não | — | Alto | Baixo: é tecnologia madura, mas exige reescrever a interface |
| **E. Mobile nativo (BeeWare/Kivy)** | Retoma a ideia do `legacy/app8.py`. | Sim | Sim | Sim | Muito alto | Alto: o Matplotlib no mobile é difícil e o empacotamento é frágil |
| ~~F. Reescrever a interface em JS/TS~~ | Interface web nativa com o núcleo portado. | Sim | Sim | Sim | Muito alto | **Descartada:** duplicaria o núcleo científico em duas linguagens |

**Recomendação: A agora, com a arquitetura preparada para C.**

- A opção A resolve notebook e escritório imediatamente e, pelo hotspot, também permite usar o
  tablet no campo sem internet.
- Se o uso no **tablet sem notebook** for essencial, fazemos uma prova de conceito curta (no
  máximo um dia) com stlite antes de qualquer compromisso. A arquitetura abaixo mantém o núcleo
  e a camada de aplicação em Python puro, compatíveis com Pyodide, para que C fique viável sem
  reescrita.
- B pode ser oferecida depois como demonstração pública, sem dados reais.

---

## 4. Arquitetura em camadas

```text
┌────────────────────────────────────────────────────────────────────┐
│ Adaptadores de entrada                                             │
│   Streamlit UI (georesistivity.app)        CLI (georesistivity.cli)│
└──────────────────────────────┬─────────────────────────────────────┘
                               │ chamam apenas funções da camada abaixo
┌──────────────────────────────▼─────────────────────────────────────┐
│ Aplicação (casos de uso, sem Streamlit)                            │
│   adicionar leitura · excluir leitura · calcular K · resumo da     │
│   estação · abrir/salvar projeto · importar CSV · exportar         │
└──────────────┬──────────────────────────────────┬──────────────────┘
               │                                  │
┌──────────────▼──────────────┐    ┌──────────────▼──────────────────┐
│ Domínio científico (puro)   │    │ Adaptadores de dados            │
│  geometry · stacking · core │    │  project (JSON) · csv_import    │
│  units · validation         │    │  io (CSV export) · autosave     │
│  models · formatting        │    │  plotting (Matplotlib)          │
└─────────────────────────────┘    └─────────────────────────────────┘
```

Regras:

1. O **domínio** não importa pandas, Matplotlib, Streamlit nem nada de I/O. Só a biblioteca
   padrão.
2. A **aplicação** recebe e devolve objetos do domínio, imutáveis, e não conhece Streamlit.
   Toda regra de negócio fica aqui ou no domínio, e é testada sem interface.
3. A **interface** só desenha telas e repassa ações. Hoje o `app/app.py` mistura validação de
   formulário com regras; isso passa para a camada de aplicação.
4. Tudo em Python puro e compatível com Pyodide, o que mantém a opção C aberta.

---

## 5. Estrutura de módulos

```text
src/georesistivity/
├── __init__.py          # API pública (importação tardia, já existe)
├── core.py              # ρa = K·ΔV/I (já existe)
├── units.py             # conversões SI (já existe)
├── validation.py        # parse_number e validações (já existe)
├── formatting.py        # exibição por localidade (já existe)
├── models.py            # Measurement, MeasurementResult (já existem) + novos modelos
├── geometry.py          # NOVO: K pela geometria (seção 7.1)
├── stacking.py          # NOVO: estatística de leituras repetidas (seção 7.2)
├── survey.py            # NOVO: Survey, SoundingPoint, Reading (seção 6)
├── services.py          # NOVO: casos de uso da camada de aplicação
├── project.py           # NOVO: arquivo de projeto JSON, schema e migrações (seção 8)
├── csv_import.py        # NOVO: importação de CSV (seção 9)
├── io.py                # exportação CSV (já existe; passa a exportar levantamentos)
├── plotting.py          # gráficos (já existe)
├── i18n/                # NOVO: catálogos pt_BR e en (seção 10)
│   ├── __init__.py
│   ├── en.py
│   └── pt_br.py
├── cli.py               # NOVO: comando `georesistivity` (seção 11)
└── app/                 # NOVO: a interface Streamlit passa a fazer parte do pacote
    ├── __init__.py
    ├── main.py          # ponto de entrada (`georesistivity app`)
    ├── state.py         # leitura e escrita tipadas do session_state
    └── pages/           # entrada de dados, levantamento, importação, exportação
app/app.py               # mantido como atalho compatível: `streamlit run app/app.py`
```

Com a interface dentro do pacote, `pip install "georesistivity[app]"` seguido de
`georesistivity app` funciona de qualquer pasta, sem precisar clonar o repositório.

---

## 6. Modelo de dados

```text
Survey (levantamento = uma SEV)
├── metadados: área, local, SEV nº, data, operador, azimute da linha AB,
│              coordenadas + CRS, equipamento, arranjo, observações
├── schedule: programação de AB/2 × MN (modelo da folha de campo, editável)
└── points: [SoundingPoint]          # um par (AB/2, MN), em ordem de aquisição
     ├── id ("P01"), AB/2, MN (comprimento total), código de marca (opcional), observações
     ├── geometric_factor: calculado pela geometria | externo (valor, unidade, fonte)
     └── readings: [Reading]         # leituras na mesma geometria
          └── ΔV, I (valores e unidades originais), data e hora,
              excluded (bool) + exclusion_reason
```

Um mesmo AB/2 aparece em mais de um ponto quando é lido com MN diferentes (superposição).
Cada ponto pertence ao segmento do seu MN.

- Todos os modelos são `dataclass(frozen=True, slots=True)`, como hoje. As alterações geram
  novas instâncias, o que facilita desfazer e manter histórico na P2.
- O `Measurement` atual continua existindo e equivale a um ponto com K externo e uma única
  leitura. A API 0.2.0 não quebra.
- Os valores calculados (SI, R, ρa, estatísticas) **não são gravados**: são recalculados ao
  abrir o projeto, para que a única fonte de verdade sejam os valores originais. As
  exportações incluem os valores calculados.

---

## 7. Decisões científicas

### 7.1 Fator geométrico K (P1.1)

Implementação base com a fórmula geral de quatro eletrodos (A e B de corrente, M e N de
potencial, em meio homogêneo semi-infinito):

```text
K = 2π / (1/AM − 1/BM − 1/AN + 1/BN)
```

Atalhos por arranjo, cada um testado contra a fórmula geral (testes de propriedade com
geometrias aleatórias):

| Arranjo | Parâmetros | K | Validações |
| --- | --- | --- | --- |
| Schlumberger | L = AB/2, l = MN/2 (MN digitado como comprimento total, como na folha) | π·(L² − l²) / (2l) | rejeitar l ≥ L; alerta informativo só quando L/l < 4 (configurável) |
| Wenner-α | a | 2πa | a > 0 |
| Dipolo-dipolo | a, n | π·n·(n+1)·(n+2)·a | a > 0, n > 0 |
| Polo-dipolo | a, n | 2π·n·(n+1)·a | a > 0, n > 0; declarar a premissa do eletrodo remoto "no infinito" |

As quatro fórmulas já foram conferidas numericamente contra a fórmula geral (diferença
relativa < 1e-14), e a de Schlumberger também contra os 45 valores da folha de campo
(seção 1.1).

Sobre o alerta de MN grande: a condição clássica AB ≥ 5·MN (l ≤ L/5) existe porque a
aproximação K ≈ πL²/(2l) supõe MN pequeno. Como usaremos a fórmula **exata**, o K continua
correto para qualquer l < L. A folha usada em campo trabalha com L/l = 4,0 (AB/2 = 1,0 m,
MN = 0,5 m) e 4,8 (AB/2 = 240 m, MN = 100 m). Um alerta em L/5 dispararia em leituras normais
e seria ignorado, então o limite padrão proposto é L/l < 4, configurável. Quando K é calculado, a fonte do K é preenchida automaticamente (por
exemplo, `calculated: schlumberger (AB/2=20 m, MN=2 m)`), e o K externo continua disponível
como hoje.

Referências que irão nas docstrings:
- Telford, W. M.; Geldart, L. P.; Sheriff, R. E. *Applied Geophysics*, 2ª ed. Cambridge
  University Press, 1990.
- Keller, G. V.; Frischknecht, F. C. *Electrical Methods in Geophysical Prospecting*.
  Pergamon, 1966.
- Loke, M. H. *Tutorial: 2-D and 3-D electrical imaging surveys*. Geotomo Software (edições
  revisadas).

### 7.2 Leituras repetidas (P1.2)

Para cada leitura i de uma estação calcula-se a resistência de transferência
`R_i = ΔV_i / I_i` [Ω]. Há dois estimadores possíveis (decisão D-7):

| Estimador | Fórmula | Comportamento |
| --- | --- | --- |
| **Média das razões** (recomendado) | ρa = K · mean(R_i) | Cada leitura pesa igual. É o que os resistivímetros fazem por *stack*, e a dispersão de R_i é a medida natural de qualidade. |
| Razão das médias (legado `APP.py`) | ρa = K · mean(ΔV_i) / mean(I_i) | Leituras com corrente maior pesam mais. Reproduz exatamente o protótipo original. |

Estatísticas por estação, sempre sobre as leituras **não excluídas**:
- n, média de R, desvio-padrão amostral (n − 1);
- coeficiente de variação CV = s / |média| em %, com alerta configurável (padrão **5%**);
- incerteza do ρa: `K · s / √n` (erro-padrão da média), usada nas barras de erro da P2;
- alerta quando as leituras têm sinais diferentes de R;
- toda exclusão manual exige um motivo, que fica gravado no projeto e aparece nas exportações.

### 7.3 Segmentos de MN

O modelo registra MN por ponto. No M3, a curva de SEV é plotada ao vivo em log-log, com
décadas fixas como no papel bilog e um segmento por MN, para mostrar os deslocamentos nas
superposições (C-06). Barras de erro e impressão no formato da folha ficam para a P2.

---

## 8. Persistência (P1.3)

Recomendação (decisão D-6): **arquivo de projeto JSON versionado + autosave**.

```json
{
  "schema": "georesistivity.project",
  "schema_version": 1,
  "created_with": "georesistivity 0.3.0",
  "survey": {
    "name": "SEV-01 (exemplo sintético)",
    "area": "",
    "local": "",
    "sev_number": "01",
    "date": "2026-10-22",
    "operator": "",
    "azimuth_deg": null,
    "location": {"latitude": null, "longitude": null, "crs": "EPSG:4326"},
    "equipment": "",
    "array": "schlumberger",
    "notes": ""
  },
  "schedule": {
    "template": "schlumberger-padrao",
    "ab2_m": [1.0, 1.3, 1.8, 2.4, 3.2, 4.2, 5.5, 7.5, 10, 13, 18, 24, 32, 42, 55, 75, 100, 130, 180, 240, 320],
    "mn_m": [0.5, 2, 5, 20, 50, 100]
  },
  "points": [
    {
      "id": "P01",
      "ab2": {"value": 1.0, "unit": "m"},
      "mn": {"value": 0.5, "unit": "m"},
      "marker": null,
      "geometric_factor": {"mode": "calculated"},
      "readings": [
        {
          "delta_v": {"value": 80, "unit": "mV"},
          "current": {"value": 40, "unit": "mA"},
          "time": "2026-10-22T09:14:00-03:00",
          "excluded": false,
          "exclusion_reason": null
        }
      ],
      "notes": ""
    }
  ]
}
```

- **Por que JSON e não SQLite:** um levantamento é pequeno (dezenas a centenas de leituras),
  o arquivo pode ser enviado por e-mail, versionado no git e lido por outros programas, e é
  fácil de inspecionar à mão. SQLite só se justificaria com muitos levantamentos consultados
  em conjunto.
- **Versionamento:** `schema_version` com funções de migração testadas. Arquivos antigos
  continuam abrindo nas versões futuras.
- **Validação ao abrir:** erros apontam o caminho do campo (por exemplo,
  `points[3].readings[1].current.value`) e nada é aceito em silêncio.
- **Autosave na opção A:** a cada alteração o projeto é gravado de forma atômica (arquivo
  temporário + `os.replace`) numa pasta do usuário (`~/GeoResistivity/autosave/`). Ao abrir o
  app, ele oferece restaurar o último projeto.
- **Na opção B:** só baixar e enviar o arquivo, sem autosave no servidor (por privacidade).
- **Na opção C:** autosave numa pasta montada em IndexedDB.

---

## 9. Importação de CSV (P1.4)

1. Detecta o dialeto: separador (`,` ou `;`), BOM e convenção decimal.
2. Mostra uma pré-visualização com o **mapeamento de colunas**. Os cabeçalhos exportados
   pelo próprio GeoResistivity (nos dois dialetos) são reconhecidos automaticamente.
3. Valida linha a linha usando `parse_number` e `MeasurementFieldError`. O relatório de
   erros diz linha, coluna e motivo; nenhuma linha inválida entra em silêncio.
4. Números ambíguos (`1,000`) seguem a regra D-1: quando o dialeto do arquivo define o
   separador decimal sem ambiguidade (por exemplo, `;` com vírgula decimal), essa convenção
   vale para o arquivo inteiro e fica declarada na pré-visualização.
5. Teste de ida e volta: exportar e depois importar gera os mesmos dados, nos dois dialetos.

---

## 10. Internacionalização (P1.5)

- Catálogos de mensagens como módulos Python (`i18n/pt_br.py`, `i18n/en.py`) com chaves
  tipadas. Um teste garante que os dois idiomas têm exatamente as mesmas chaves e os mesmos
  marcadores (`{field}`, `{value}`).
- PT-BR é o padrão, junto com o formato numérico pt-BR que já existe.
- As mensagens de erro do núcleo continuam em inglês, porque são API para programadores. A
  interface traduz pelo código do erro (`MeasurementFieldError.field` e um código de motivo),
  e não pelo texto.
- Escolhi catálogos em Python em vez de `gettext` porque são dois idiomas, um único
  mantenedor e não exigem ferramentas de compilação. Se surgirem tradutores externos, a
  migração para `gettext` é mecânica.

---

## 11. Linha de comando

`argparse` da biblioteca padrão, sem dependência nova:

```text
georesistivity app                         # abre a interface (precisa do extra [app])
georesistivity calc --dv 125mV --i 35mA --k 625m
georesistivity k schlumberger --ab2 20m --mn2 1m
georesistivity import medidas.csv -o levantamento.geores.json
georesistivity export levantamento.geores.json --format excel-pt-br -o medidas.csv
```

---

## 12. Qualidade e entrega

- Cada marco (seção 14) é uma sequência de commits pequenos com testes, documentação e
  entrada no CHANGELOG, como na Fase 2.
- Testes por camada: domínio (valores calculados à mão + propriedades), aplicação (casos de
  uso sem Streamlit), projeto (migrações e ida e volta), interface (AppTest).
- Os gates atuais continuam: Ruff, `mypy --strict`, cobertura ≥ 95% e matriz da CI.
- Lockfile para o app (S-04), definido junto com a opção de execução: `uv lock` ou
  `pip-compile` para A e B; o stlite tem fixação de pacotes própria.

---

## 13. Decisões

| ID | Decisão | Recomendação e status |
| --- | --- | --- |
| D-5 | Onde o app vai rodar no campo (seção 3) | **A — Streamlit local**, com acesso pelo tablet via hotspot e a arquitetura pronta para C. **Aprovada.** |
| D-6 | Persistência (seção 8) | **Arquivo de projeto JSON + autosave**. **Aprovada.** |
| D-7 | Estimador das leituras repetidas (seção 7.2) | **Média das razões**, K · mean(ΔV_i/I_i). **Aprovada.** |
| D-8 | Arranjos do cálculo de K na P1 (seção 7.1) | **Schlumberger como fluxo principal**, com a folha de campo digital, como na folha real. Wenner, dipolo-dipolo, polo-dipolo e a fórmula geral só como calculadoras de K, porque o custo é baixo e já estão conferidas. **Aprovada.** |
| D-9 | Detalhes da folha de campo (seção 1.1) | Confirmar: (a) o que é o segundo par de colunas ΔV/I à direita (leitura repetida? leitura de superposição com o próximo MN?); (b) o que significam os códigos VN, VD, AM, AZ, VM… ao lado de AB/2 (cores de marcação no cabo?). **Respondida:** (a) é a leitura de superposição com o próximo MN no mesmo AB/2; (b) são as cores de marcação no cabo/carretel para cada AB/2. |

Decisões técnicas que tomei e que você pode reverter: camadas da seção 4, catálogos de i18n
em Python (seção 10), `argparse` (seção 11), alerta de CV em 5% (seção 7.2).

---

## 14. Roteiro da P1

| Marco | Entrega | Demonstrável |
| --- | --- | --- |
| **M1 — Reestruturação** | Interface dentro do pacote, `state.py`, `services.py`, `georesistivity app`, atalho `app/app.py`. Nenhuma mudança de comportamento. | O app abre por `georesistivity app`; todos os testes passam. |
| **M2 — Geometria e K** | `geometry.py`, modo "K externo / calcular", MN registrado, fonte do K preenchida automaticamente, teste de regressão com a tabela de K da folha. | Calcular K de uma SEV Schlumberger pela tela e pela CLI; reproduzir a tabela de K da folha. |
| **M3 — Folha de campo digital e leituras repetidas** | `survey.py`, `stacking.py`, modelo de programação AB/2 × MN, tabela editável em que só se digita ΔV e I, curva log-log ao vivo com um segmento por MN, exclusão com motivo, estatísticas e alertas. | Preencher uma SEV sintética como na folha de papel e ver a curva se formar. |
| **M4 — Persistência** | `project.py` (schema v1), salvar e abrir, autosave e restauração, formulário de metadados. | Fechar o navegador, reabrir e recuperar tudo. |
| **M5 — Importação CSV** | `csv_import.py`, pré-visualização, mapeamento, relatório de erros, ida e volta. | Importar o CSV de exemplo e um CSV do Excel pt-BR. |
| **M6 — Bilíngue** | `i18n/`, seletor de idioma, testes de completude. | Trocar PT-BR ↔ EN sem recarregar dados. |

**Andamento:** M1 concluído em 2026-10-22: interface em `georesistivity.app`, regras em
`services.py`, comando `georesistivity app` (só `localhost` por padrão; `--lan` para o
tablet).

**Andamento:** M2 concluído em 2026-10-22: `geometry.py` com os quatro arranjos e a fórmula
geral, modo "Calcular K (Schlumberger)" na tela, MN gravado nas medições, calculadora de K,
comandos `georesistivity k`, `k table` e `calc`. Os 45 valores de K da folha de campo viraram
teste de regressão.

**Andamento:** M3 concluído em 2026-10-22: aba "Folha de campo (SEV)" com os 45 pares
(AB/2, MN) da folha, leituras de superposição como segmentos de MN, leituras repetidas pela
média de ΔV/I com CV e limite configurável, exclusão com motivo, coluna de cor, curva log-log ao
vivo com décadas iguais e exportação de pontos e leituras. A camada de aplicação da folha ficou
em `field_sheet.py` (em vez de `services.py`), e o modelo de sondagem em `survey.py`.
Observação: o `AppTest` do Streamlit não digita em `st.data_editor`; a lógica da folha é
testada sem interface e a digitação foi conferida no navegador.

**Andamento:** M4 concluído em 2026-10-22: arquivo de projeto `.geores.json` (schema v1)
com a folha **exatamente como digitada** (inclusive linhas em branco ou incompletas, para que
o autosave nunca perca trabalho em andamento), metadados do cabeçalho da folha, abrir e salvar,
autosave atômico com um arquivo por sessão, recuperação após recarregar e modelos de folha
com as cores de marcação. Diferença em relação à seção 8: as células numéricas da folha são
gravadas como texto digitado (e não como valor + unidade por leitura), e o horário de cada
leitura ainda não é registrado; fica para a P2, junto com o histórico de alterações.

**Andamento:** M5 concluído em 2026-10-22: aba "Importar CSV" para a folha de campo e para
as medições avulsas, com leitura de UTF-8 e Windows-1252 (Excel em português), separador
`;`/`,`/tab e linha `sep=`, convenção decimal única por arquivo (D-1), mapeamento automático e
editável das colunas, relatório de cada linha recusada (linha, coluna, motivo) e ida e volta
exata com os próprios CSVs nos dois formatos. Os valores importados são gravados na folha como
texto sem ambiguidade (`1,234` vira `1,2340`), para que a regra D-1 não os recuse depois.

**Andamento:** M6 concluído em 2026-10-22, e com ele a **P1**: interface em português do Brasil
(padrão) e inglês, com seletor de idioma; catálogos `app/i18n/pt_br.py` e `en.py` com teste
de mesmas chaves e marcadores; erros do núcleo traduzidos por código
(`georesistivity.messages`), nunca pelo texto; rótulos dos gráficos traduzíveis. Os arquivos
(CSV, projeto) e a linha de comando continuam em inglês, para não depender do idioma da tela.
Os poucos textos internos do botão de envio de arquivo do Streamlit não são traduzíveis.

**Consolidação:** a P1 foi trazida para a `main` local em 2026-10-22 como versão `0.3.0`
(seção correspondente do `CHANGELOG.md`). As branches de cada fase e marco foram mantidas.

**Ponto de parada:** ao final do M6 eu paro, rodo o app e mostro capturas, conforme o plano.
Também posso parar ao fim de cada marco, se você preferir revisar aos poucos.

Depois da P1 (sem começar sem a sua aprovação):
- **P2:** curva de SEV por segmento de MN com barras de erro; exportação de figura;
  relatório PDF/HTML; edição de qualquer leitura com histórico. Proposta na seção 15.
- **P3 (aprovação explícita):** modelagem direta e inversão 1D; sugestão do tipo de curva.

---

## 15. Proposta da P2

**Status:** aprovada em 2026-10-22: ordem M7 → M10 e decisões D-10 a D-14. A D-15 será
respondida antes do M8.

### 15.1 Ponto de partida

| Item | O que a P1 já tem | O que falta |
| --- | --- | --- |
| Curva com barras de erro | Erro-padrão do ρa por posição, `K · s / √n` (`PointResult.standard_error_ohm_m`), já exportado no CSV de pontos; curva bilog com um segmento por MN. | Desenhar as barras, dizer na legenda o que elas representam e mostrar o erro na tabela de posições. |
| Exportação de figura | Figura matplotlib da curva, com rótulos traduzíveis. | Arquivos PNG, SVG e PDF; título com os dados da SEV; opção de escala do papel bilog. |
| Relatório PDF/HTML | Todos os dados e cálculos. | O documento, e textos traduzíveis fora da interface (para a CLI). |
| Edição com histórico | Folha gravada exatamente como digitada; exclusão com motivo obrigatório. | Identidade estável de cada linha, horário de cada leitura, registro das alterações, desfazer; formato de projeto v2. |

**Atenção às barras de erro:** só existe erro-padrão onde há duas ou mais leituras válidas na
mesma posição. Na folha de campo a maioria das posições tem uma leitura só, então a curva vai
ter barras em poucas posições. É o comportamento correto (o programa não inventa incerteza),
mas convém saber antes.

### 15.2 Ordem proposta

| Marco | Entrega | Demonstrável | Tamanho |
| --- | --- | --- | --- |
| **M7 — Barras de erro** | Barra de ±1 erro-padrão em cada posição com n ≥ 2, na cor do segmento de MN; legenda dizendo o que a barra é; se ρa − erro ≤ 0 (impossível em eixo log), a barra inferior vai até a borda do gráfico e a posição recebe aviso; coluna de erro na tabela de posições; opção de mostrar ou ocultar as barras. | A SEV sintética mostra a barra na posição repetida; ligar e desligar. | Pequeno |
| **M8 — Exportação de figura** | PNG (300 dpi), SVG e PDF vetorial da curva; título opcional com SEV nº, local e data; tamanho "tela" ou **escala do papel bilog** (milímetros por década, para sobrepor às curvas-padrão); nome do arquivo a partir do projeto; comando `georesistivity plot projeto.geores.json -o curva.pdf`. | Baixar os três formatos; imprimir o PDF em 100% e medir uma década com régua. | Pequeno |
| **M9 — Edição com histórico** | Formato de projeto v2 com migração do v1; identificador oculto e estável em cada linha; horário em que cada leitura ficou completa; registro automático de cada alteração de valor já digitado (antes e depois, linha, coluna, horário), de linhas apagadas e de trocas da folha (importação, nova folha); painel "Histórico" com filtro por linha e botão **Desfazer última alteração**; histórico exportável em CSV. | Digitar, corrigir um ΔV, apagar uma linha, desfazer, fechar, reabrir o projeto e encontrar o histórico intacto. | Grande |
| **M10 — Relatório PDF/HTML** | Módulo `report.py` que monta o conteúdo uma vez e o desenha em dois formatos: HTML autocontido (figura SVG embutida, abre sem internet, imprime bem) e PDF A4. Conteúdo: cabeçalho da folha, curva com barras, tabela de posições, leituras com exclusões e motivos, alertas, histórico, fórmulas e referências, versão do programa, data de geração e SHA-256 do arquivo de projeto. Comando `georesistivity report`. | Gerar os dois relatórios da SEV sintética, em português e em inglês. | Médio |

**Por que essa ordem:**
1. M7 e M8 são pequenos, de baixo risco, mexem só no gráfico e dão resultado visível logo. O
   relatório reaproveita os dois.
2. O M9 vem **antes** do relatório porque muda o formato do projeto e cria dados (horário das
   leituras, histórico) que o relatório precisa mostrar. Na ordem inversa, o relatório seria
   refeito.
3. O M10 fecha a P2 porque junta tudo.

**Alternativa:** começar pelo M9, se você pretende usar o programa em campo logo. Assim todo
dado digitado já nasce com histórico; o custo é adiar as entregas visuais.

**Ponto de parada:** ao fim de cada marco, com demonstração, como na P1.

### 15.3 Decisões

| ID | Decisão | Recomendação e status |
| --- | --- | --- |
| D-10 | O que a barra de erro representa | **±1 erro-padrão da média** (`K · s / √n`), como previsto na seção 7.2, só com n ≥ 2. Alternativas: intervalo de 95% com t de Student (com n = 2 a barra é 12,7 vezes o erro-padrão e domina a curva) ou ±1 desvio-padrão (mostra a dispersão das leituras, não a incerteza do ρa). **Aprovada.** |
| D-11 | Idioma do relatório | **O idioma da interface no momento da geração** (PT-BR por padrão), com números no formato escolhido. É uma exceção à regra "arquivos em inglês", porque o relatório é lido por pessoas; CSV e projeto continuam em inglês. **Aprovada.** |
| D-12 | Como gerar o PDF | **Sem dependência nova:** HTML autocontido e PDF desenhado com o matplotlib, que já é dependência. O WeasyPrint exige bibliotecas do sistema (Pango), difíceis de instalar no Windows; o ReportLab seria mais uma dependência para manter. **Aprovada.** |
| D-13 | Política do histórico | **Registro automático, sem exigir motivo:** toda alteração de valor já digitado, toda linha apagada e toda troca da folha entram no histórico com horário; digitar numa célula vazia não conta como alteração. A exclusão continua exigindo motivo. Alternativa mais rígida, no estilo das boas práticas de laboratório: exigir motivo para corrigir uma leitura completa. É mais rastreável, mas atrapalha a digitação em campo. **Aprovada.** |
| D-14 | Horário da leitura | **Automático:** o momento em que ΔV e I da linha ficaram completos, gravado como "digitado em". Quando a folha é passada a limpo no escritório, esse é o horário da digitação, não o da medição, e o relatório diz isso. Como a folha de papel não tem coluna de hora, não proponho hora digitada à mão. **Aprovada.** |
| D-15 | Escala do papel bilog | Preciso do **módulo do papel que você usa** (tamanho de uma década, em mm) para usar como padrão na exportação em escala. O valor fica configurável. **Pendente:** o M8 usa 50 mm como padrão provisório. |

### 15.4 Notas técnicas

- Os catálogos de texto saem de `georesistivity.app.i18n` (que importa o Streamlit) para um
  módulo `georesistivity.i18n` sem Streamlit, para que o relatório e a CLI usem os mesmos
  textos da tela. A interface continua usando `t()`.
- No HTML, todo texto digitado (local, notas, motivos) passa por `html.escape`, para que um
  projeto não consiga injetar código no relatório (mesma ideia do S-01 no CSV).
- Identidade de linha: coluna oculta no `st.data_editor`; linhas novas recebem identificador na
  hora. A comparação entre o estado anterior e o atual da folha é uma função pura
  (`diff_sheet`), testada sem interface.
- Formato v2 do projeto, com migração automática do v1 (identificadores novos, horários vazios,
  histórico vazio). Um arquivo v1 de exemplo fica nos testes para garantir que continua abrindo.

```json
{
  "sheet": {
    "rows": [
      {"id": "r0007", "marker": "VD", "ab2": "10", "mn": "2", "delta_v": "82,0",
       "current": "41,5", "excluded": false, "reason": "",
       "entered_at": "2026-10-22T09:14:03-03:00"}
    ]
  },
  "history": [
    {"at": "2026-10-22T09:20:11-03:00", "action": "edit", "row": "r0007",
     "field": "delta_v", "old": "80,2", "new": "82,0"},
    {"at": "2026-10-22T09:31:40-03:00", "action": "delete_row", "row": "r0012",
     "old_row": {"ab2": "13", "mn": "2", "delta_v": "51,3", "current": "40,8"}}
  ]
}
```

- Fora da P2, como antes: o teclado numérico no celular (seção 16) e qualquer item da P3.

**Andamento:** M7 concluído em 2026-10-22: barras de ±1 erro-padrão na curva (D-10), na cor do
segmento de MN, com entrada na legenda, chave para ligar e desligar e uma nota dizendo
quantas posições têm barra; coluna de erro-padrão na tabela de posições; eixos estendidos até
as pontas das barras. Constatação: com leituras todas positivas o erro-padrão é sempre menor
que o próprio ρa (o CV de n valores positivos é menor que √n). Por isso a barra só
cruza o zero com leituras de sinais opostos (que já recebem aviso) ou com uma leitura zero; nos
dois casos a parte de baixo fica pontilhada até a borda e a posição é circulada.
Conferido no navegador: na curva da tela (uma década tem cerca de 160 pixels), a barra só passa
do marcador quando o erro-padrão é maior que cerca de 5% do ρa, ou cerca de 10% nas posições
circuladas. Abaixo disso, o valor é lido na coluna de erro-padrão da tabela de posições.

**Andamento:** M8 concluído em 2026-10-23: exportação da curva em PNG (300 dpi), SVG e PDF, no
tamanho padrão ou na **escala do papel bilog**, em que a área do gráfico mede exatamente o
número de décadas vezes o módulo nos dois eixos; título opcional com SEV nº, local e data;
nome do arquivo a partir do projeto; arquivos reproduzíveis (sem data de criação) e fontes do
PDF embutidas como TrueType; comando `georesistivity plot`. O módulo padrão é **provisório**,
50 mm por década, escolhido para que as 3 × 4 décadas da folha caibam em A4 impresso em 100%;
não é o módulo de nenhum papel. A D-15 continua pendente. Para a CLI rotular a figura em
português, os catálogos de texto passaram de `georesistivity.app.i18n` para
`georesistivity.i18n` (prevista na seção 15.4 para o M10). O botão gera o arquivo só no clique,
para que a figura em 300 dpi não seja redesenhada a cada célula digitada.

---

## 16. Riscos

| Risco | Mitigação |
| --- | --- |
| O estado da interface Streamlit fica complexo com várias telas. | A lógica fica em `services.py`, testada sem Streamlit; o `state.py` concentra o acesso tipado ao `session_state`. |
| Mudança de formato de projeto quebrar arquivos antigos. | `schema_version`, migrações testadas e arquivos de exemplo de cada versão nos testes. |
| O stlite (opção C) não suportar a versão do Streamlit usada. | Prova de conceito curta antes de qualquer compromisso; o núcleo e os serviços não dependem disso. |
| A tabela editável do Streamlit (`st.data_editor`) interpretar números pela localidade do navegador, fugindo da regra D-1. | As colunas ΔV e I são de texto e cada célula passa por `parse_number`; uma coluna de status mostra o erro da linha. |
| O teclado numérico no celular continuar alfabético. | Na opção A/B, documentar e avaliar um componente pequeno de entrada numérica. Ficou fora da P2 (seção 15); entra se o uso em campo pedir. |
| A coluna oculta de identificador da folha não sobreviver a alguma operação do `st.data_editor` (ordenar, colar várias linhas). | Conferir no navegador, no M9, ordenar, colar e apagar linhas. Se alguma operação perder o identificador, a linha é registrada no histórico como substituída, e nada se perde. |
| O histórico deixar o autosave lento. | Cada alteração ocupa cerca de 200 bytes no JSON indentado; mil alterações são cerca de 200 kB. Medir no M9 e, se preciso, gravar o histórico em arquivo separado. |
| Crescimento de escopo. | Marcos curtos e pontos de parada; a P3 só começa com aprovação explícita. |
