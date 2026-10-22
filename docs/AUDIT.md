# Auditoria técnica — GeoResistivity (Fase 1)

- **Data:** 2026-10-22
- **Versão auditada:** `0.1.0` (zip do GitHub, commit local de baseline `5ee657a`)
- **Ambiente:** macOS, Python 3.13.13, Streamlit 1.66.1, pandas 3.1.0, Matplotlib 3.11.2
- **Escopo:** `src/georesistivity/`, `app/app.py`, `tests/`, `examples/`, `pyproject.toml`,
  `.github/workflows/ci.yml`, `.gitignore`, `README.md`, `legacy/`
- **Método:** leitura integral do código, execução da suíte de testes e das ferramentas de
  qualidade, provas de conceito com o núcleo em Python, testes da interface com
  `streamlit.testing.v1.AppTest` e inspeção visual no navegador em viewport de celular
  (375×812).

Nenhum arquivo de código foi alterado nesta fase.

---

## 1. Resumo executivo

O projeto tem uma base sólida. O núcleo científico é separado da interface, os modelos são
imutáveis, as conversões de unidade são explícitas, a cobertura de testes é de 97% e o README
é honesto sobre as limitações. A equação, as unidades e a análise dimensional estão corretas.

Os problemas estão na **entrada de dados** e na **operação real**:

1. Há um caminho em que o software **calcula um resultado errado, mostra mensagem de sucesso e
   não avisa nada**: números com separador de milhar (`1,000` ou `3.134`) são lidos como
   decimais. Para o público brasileiro, que escreve `3.134` querendo dizer três mil cento e
   trinta e quatro, isso é plausível, e valores de K nessa faixa são comuns em SEV
   Schlumberger.
2. Valores fisicamente suspeitos (K ≤ 0, AB/2 ≤ 0, ρa < 0) entram sem nenhum aviso.
3. Para uso em campo, a perda de dados ao recarregar a página, a ausência de tradução para o
   português e a experiência no celular são as principais barreiras.

| Severidade | Quantidade |
| --- | ---: |
| Crítica | 1 |
| Alta | 2 |
| Média | 12 |
| Baixa | 10 |
| Sugestão | 7 |
| Verificar (depende do histórico do GitHub) | 1 |

### Os 10 achados mais importantes

| # | ID | Severidade | Achado |
| ---: | --- | --- | --- |
| 1 | V-01 | Crítica | `1,000` e `3.134` viram 1.0 e 3.134 em silêncio. ρa sai 1000× errado com mensagem de sucesso. |
| 2 | U-03 | Alta | Medições existem só na sessão. Recarregar a página ou perder a conexão apaga tudo. |
| 3 | C-01 | Alta | K ≤ 0, AB/2 ≤ 0 e ρa < 0 são aceitos sem aviso. |
| 4 | S-01 | Média | Injeção de fórmula no CSV pelo campo livre "K source". |
| 5 | I-01 | Média | CSV sem BOM e só no dialeto inglês: o `µ` corrompe e o arquivo não abre em colunas no Excel pt-BR. |
| 6 | U-01 | Média | A mensagem de erro não diz qual campo está errado. |
| 7 | U-02 | Média | O formulário mantém os valores após o envio; um clique duplo grava uma medição duplicada. |
| 8 | C-04 | Média | A exibição com `:,.2f` mostra `0.00` para ρa pequeno e usa vírgula de milhar no padrão inglês. |
| 9 | C-05 | Média | Faltam MN/2, data/hora e identificação da estação, apesar de o README falar em "traceable workflow". |
| 10 | U-04 | Média | No celular, a barra lateral abre cobrindo a tela e os campos numéricos abrem o teclado de letras. |

---

## 2. Baseline de qualidade

| Verificação | Resultado |
| --- | --- |
| `pytest` | **53 passed** (confere com o README) |
| `ruff check .` | sem problemas |
| `ruff format --check .` | 15 arquivos formatados |
| Cobertura (`pytest-cov`) | **97%** no núcleo. Linhas não cobertas: `core.py:38`, `plotting.py:59, 61`, `validation.py:10` |
| `mypy --strict src app` | **2 erros** (ver Q-01) |
| `pip-audit` | nenhuma vulnerabilidade conhecida nas dependências |
| Testes de interface | **nenhum** |
| `import georesistivity` | ~450 ms (pandas ~260 ms + Matplotlib ~160 ms) |

---

## 3. Achados

Formato: **ID — título** · severidade · categoria · local. Depois vêm a evidência e a
correção proposta.

### 3.1 Validação de entrada

#### V-01 — Separador de milhar é lido como decimal, sem aviso
**Crítica** · correção científica / validação · `src/georesistivity/validation.py:26-29`

`parse_number` troca qualquer vírgula por ponto e chama `float()`. Um único separador é sempre
tratado como decimal.

Evidência (núcleo):

```text
parse_number("1,000")  -> 1.0
parse_number("3.134")  -> 3.134    (em pt-BR significa 3134)
```

Evidência (interface, via AppTest): ΔV = `125` mV, I = `35` mA, K = `1,000` m. O app mostra
"Measurement added to this session." e **ρa = 3.57 Ω·m**. O valor pretendido era 3 571,43 Ω·m.

O README diz "Rejection of ambiguous numeric formats" (linha 59) e "thousands separators are
not explicitly supported" (linha 126). Na prática eles não são rejeitados: são interpretados
em silêncio com outro significado.

**Correção proposta:** tratar como ambíguo qualquer número com **um único separador seguido de
exatamente três dígitos e parte inteira diferente de zero** (`1,000`, `3.134`, `12,500`).
Opções (decisão D-1):
- (a) rejeitar com uma mensagem que oriente ("use 1000 ou 1,0");
- (b) adicionar uma preferência explícita de formato numérico (pt-BR ou en) e interpretar de
  acordo;
- (c) aceitar, mas exibir o valor interpretado e pedir confirmação.

`0,125` e `0.125` continuam válidos, porque a parte inteira zero nunca é agrupamento de milhar.

#### V-02 — `float()` aceita sintaxes que o usuário não espera
**Baixa** · validação · `src/georesistivity/validation.py:31`

```text
"1_000" -> 1000.0      (sublinhado de literal Python)
"١٢"    -> 12.0        (dígitos arábico-índicos)
"１２"   -> 12.0        (dígitos de largura total)
"1e3"   -> 1000.0      (notação científica: útil, mas não documentada)
```

**Correção:** validar contra uma expressão regular explícita (ASCII, sinal opcional, um
separador decimal, expoente opcional) antes de converter. Documentar o suporte a notação
científica.

#### V-03 — Unidade com `μ` grego (U+03BC) é rejeitada no núcleo
**Baixa** · validação · `src/georesistivity/units.py:7-19`

O núcleo aceita `µ` (U+00B5, MICRO SIGN) e `u`, mas não `μ` (U+03BC), que é o caractere que
teclados gregos e muitos textos copiados produzem. A interface não é afetada porque usa
listas de seleção. Afeta a futura importação de CSV.

**Correção:** normalizar as unidades com `unicodedata.normalize("NFKC", ...)` e aceitar
explicitamente U+03BC.

### 3.2 Correção científica

A equação ρa = K·ΔV/I, a análise dimensional (m · V/A = Ω·m) e as conversões para o SI estão
corretas. O exemplo do README (125 mV, 35 mA, K = 625 m → 2232,142857 Ω·m) confere, e o
dataset de exemplo é consistente com a fórmula (já coberto por teste).

#### C-01 — Valores fisicamente suspeitos entram sem aviso
**Alta** · ciência · `src/georesistivity/core.py:31-34`, `src/georesistivity/units.py:43`

| Entrada | Comportamento atual |
| --- | --- |
| K = −5 m | aceito, ρa = −25 Ω·m |
| ΔV = −100 mV | aceito, ρa = −25 Ω·m |
| AB/2 = −3 m | aceito e plotado em escala linear |
| AB/2 = 0 m | aceito |

Em arranjos convencionais K > 0 e AB/2 > 0. Um ρa negativo quase sempre indica polaridade
invertida, cabo trocado ou erro de leitura. A interface exibe "−2,232.14 ohm·m" sem nenhum
alerta. O teste `test_negative_values_keep_their_mathematical_sign` congela esse comportamento
como intencional.

**Correção proposta (decisão D-2):**
- rejeitar K ≤ 0 e AB/2 ≤ 0;
- aceitar ΔV e I negativos (o sinal depende da convenção de aquisição), mas emitir um **aviso
  tipado** quando ρa < 0, mostrado na interface e registrado numa coluna de qualidade no CSV.

#### C-02 — Conversão de unidade não verifica o resultado
**Baixa** · robustez · `src/georesistivity/units.py:43`

`_convert_to_si` valida a entrada, mas não o produto.

```text
AB/2 = 1e306 km   -> spacing_ab2_m = inf  (armazenado e plotado sem erro)
K    = 1e306 km   -> erro "geometric_factor_m must be finite" (mensagem confusa)
I    = 1e-320 µA  -> erro "current_a cannot be zero" (o usuário digitou um valor diferente de zero)
```

São valores extremos, mas o `inf` em AB/2 passa por todas as verificações e chega até o
gráfico.

**Correção:** verificar a finitude após a conversão e rejeitar o underflow para zero com uma
mensagem própria.

#### C-03 — Artefatos de ponto flutuante nos valores SI exportados
**Baixa** · precisão / apresentação · `src/georesistivity/units.py:7-26, 43`

A conversão multiplica por `1e-3`/`1e-6`. Em 717 de 4000 valores inteiros testados (1–1000 em
mV, µV, mA e cm), o resultado difere do arredondamento correto:

```text
9 mV   -> 0.009000000000000001 V
100 µV -> 9.999999999999999e-05 V   (aparece assim no CSV)
```

O erro é de 1 ULP e não afeta a ciência, mas aparece no CSV e passa uma impressão de
imprecisão.

**Correção:** dividir por potências de dez (`value / 1e3`) em vez de multiplicar por `1e-3`,
ou definir `float_format` com dígitos significativos na exportação, mantendo a precisão total
internamente.

#### C-04 — A exibição perde informação e usa o padrão numérico inglês
**Média** · apresentação científica · `app/app.py:150`

`f"{rho:,.2f}"` produz:
- `0.00 ohm·m` para ρa = 0,0029 Ω·m (ΔV pequeno com K pequeno);
- `2,232.14`, que um usuário brasileiro lê como 2,23. O próprio formulário aceita vírgula
  decimal, então a interface mistura as duas convenções.

**Correção:** formatar com dígitos significativos (ex.: 4 a 6) e com a localidade escolhida
pelo usuário.

#### C-05 — Faltam dados de rastreabilidade de campo
**Média** · completude científica · `src/georesistivity/models.py:7-18`

O README promete um "traceable workflow" (linha 28), mas o registro não tem MN/2, data e hora,
identificador de estação ou ponto, nem observações. Em SEV Schlumberger, as trocas de MN geram
leituras repetidas no mesmo AB/2 (segmentos de superposição). Sem MN/2 não dá para distinguir
esses segmentos nem detectar os deslocamentos de curva típicos.

**Correção:** incluir MN/2 (opcional) e um carimbo de data e hora no modelo. Isso prepara o
cálculo de K pela geometria na Fase 3.

#### C-06 — O gráfico liga os pontos na ordem de aquisição por padrão
**Baixa** · visualização · `src/georesistivity/plotting.py:38`, `app/app.py:253`

Com "Sort by AB/2" desmarcado (padrão), a linha segue a ordem de aquisição. Se a aquisição não
foi monotônica, ou se há AB/2 repetidos (troca de MN), a curva faz zigue-zague ou traços
verticais. Para uma curva de SEV, o padrão esperado é ordenar por AB/2 e separar os segmentos
por MN.

**Correção:** ordenar por AB/2 por padrão e, quando houver MN/2, plotar um segmento por MN.

#### C-07 — Funcionalidades dos protótipos legados que se perderam
**Sugestão** · escopo · `legacy/APP.py`, `legacy/app6.py`, `legacy/app7.py`

- `APP.py` fazia a média de 3 leituras (ΔV₁..₃ e I₁..₃) por estação.
- `app6.py` e `app7.py` salvavam o gráfico em PNG.

A versão moderna não faz nenhuma das duas coisas. Observação para a Fase 3: o legado calculava
`mean(ΔV) / mean(I)`, que é um estimador diferente de `mean(ΔV / I)`. A escolha precisa ser
explícita e documentada.

#### C-08 — Os valores de K do dataset de exemplo não seguem uma geometria
**Sugestão** · dados de exemplo · `examples/sample_measurements.csv`

Os K são sintéticos e não correspondem a uma geometria Schlumberger com MN fixo. Isso não é um
erro hoje, porque o K é externo. Quando o cálculo de K entrar (Fase 3), vale regenerar o
exemplo a partir de uma geometria declarada.

### 3.3 Interface (UX e acessibilidade)

#### U-01 — A mensagem de erro não identifica o campo
**Média** · UX · `app/app.py:117-132`

Com o campo Current vazio, a mensagem é "Measurement could not be added: value cannot be
empty". Com Current = `abc`, é "invalid numeric value: 'abc'". Nos dois casos o usuário não
sabe qual dos cinco campos causou o problema.

**Correção:** validar campo a campo e mostrar o erro com o nome do campo (e, se possível,
perto dele).

#### U-02 — Envio duplicado e edição limitada
**Média** · UX / integridade de dados · `app/app.py:77`

`st.form` usa `clear_on_submit=False` (padrão), então os valores continuam no formulário. Dois
cliques em "Calculate and add measurement" gravam duas linhas idênticas (confirmado com
AppTest). Só é possível remover a **última** medição; não existe edição nem remoção de uma
linha qualquer.

**Correção:** limpar só os campos de valor (manter as unidades), avisar quando a medição for
idêntica à anterior e permitir editar ou excluir qualquer linha.

#### U-03 — Dados só na sessão
**Alta** · operação · `app/app.py:24-28`

É uma limitação documentada no README, mas é o maior risco operacional para uso real:
recarregar a página, perder a conexão, deixar a sessão expirar ou reiniciar o servidor apaga
todas as medições.

**Correção (Fase 3):** projeto salvo em arquivo, autosave e importação do próprio CSV ou JSON.

#### U-04 — Experiência ruim no celular
**Média** · UX de campo · `app/app.py:80-105, 285`

Verificado no navegador em 375×812:
- `initial_sidebar_state="expanded"` faz a barra lateral abrir **cobrindo a tela inteira**, e
  o usuário precisa fechá-la toda vez;
- nenhum `<input>` tem `inputmode` (verificado no DOM), então os campos numéricos abrem o
  teclado alfabético;
- o botão "Deploy" do modo de desenvolvimento aparece na barra superior.

**Correção:** usar `initial_sidebar_state="auto"` e `client.toolbarMode = "viewer"`. Para o
teclado numérico, o `st.text_input` não expõe `inputmode`, o que pesa na decisão de
arquitetura da Fase 3.

#### U-05 — Interface só em inglês
**Média** · i18n · `app/app.py`

O público-alvo provável fala português (os protótipos legados eram em português). Rótulos,
mensagens e formato numérico estão em inglês.

#### U-06 — Notação de unidade inconsistente
**Baixa** · apresentação · `app/app.py:52, 150`, `src/georesistivity/plotting.py:78`, `src/georesistivity/io.py:24`

A mesma unidade aparece como `ohm.m` (barra lateral, gráfico, CSV), `ohm·m` (métrica) e `Ω·m`
(README).

**Correção:** usar `Ω·m` na interface e no gráfico. Manter `ohm.m` no cabeçalho do CSV só se
for preciso compatibilidade ASCII.

#### U-07 — O seletor de escala pode ficar vazio
**Baixa** · UX · `app/app.py:255-259`

`st.segmented_control` usa `required=False` (padrão), então o usuário pode desmarcar a opção.
Nesse caso o gráfico fica em escala linear sem nenhuma opção destacada.

**Correção:** passar `required=True`.

### 3.4 Arquitetura, empacotamento e qualidade de código

#### Q-01 — `mypy --strict` aponta 2 erros
**Baixa** · tipagem

```text
src/georesistivity/core.py:61: Argument 2 to "convert_length_to_meters" has incompatible type "str | None"; expected "str"
app/app.py:273: Argument "scale" to "create_resistivity_figure" has incompatible type "str"; expected "Literal['linear', 'log-log']"
```

O primeiro está protegido em tempo de execução pelo `__post_init__`, mas o sistema de tipos
não sabe disso. O segundo é um `str` que deveria ser `PlotScale`. Também falta o marcador
`py.typed`.

#### Q-02 — Empacotamento inconsistente
**Média** · empacotamento · `pyproject.toml:5-14`

- O nome da distribuição (`georesistivity-calculator`) é diferente do pacote
  (`georesistivity`).
- A descrição diz "Scientific core", mas **Streamlit é dependência obrigatória**. Quem quiser
  só a biblioteca instala o servidor web inteiro. O núcleo deveria depender só do essencial e
  ter extras `[app]` e `[dev]`.
- Não há `__version__`, `license`, `authors`, `classifiers`, `urls` nem ponto de entrada
  (`[project.scripts]`).

#### Q-03 — Sem licença
**Média** · legal · raiz do repositório

Não há arquivo `LICENSE` e o README não menciona licença. Sem licença, o código é "todos os
direitos reservados" e ninguém pode legalmente usar, modificar ou redistribuir. Precisa ser
resolvido antes de distribuir o software (decisão D-3).

#### Q-04 — Importar o núcleo carrega pandas e Matplotlib
**Sugestão** · desempenho · `src/georesistivity/__init__.py:4-16`

`import georesistivity` leva ~450 ms porque o `__init__` reexporta `io` (pandas) e `plotting`
(Matplotlib). Para CLI e scripts, convém importação tardia ou subpacotes opcionais. O pandas
pode até ser substituído pelo módulo `csv` da biblioteca padrão na exportação.

#### Q-05 — Pequenas duplicações na interface
**Sugestão** · manutenção · `app/app.py:244, 261`

`prepare_plot_points` é chamada duas vezes em `render_plot`, uma só para contar os pontos.

### 3.5 Testes e CI

#### T-01 — Teste depende do diretório atual
**Baixa** · testes · `tests/test_io.py:82`

`Path("examples/sample_measurements.csv")` é relativo ao diretório atual. Rodando de dentro de
`tests/`: **1 failed, 3 passed**.

**Correção:** `Path(__file__).resolve().parents[1] / "examples" / ...`.

#### T-02 — A interface não tem testes
**Média** · testes · `app/app.py`

Nenhum teste cobre a interface. Os achados V-01, U-01, U-02 e U-07 foram todos reproduzidos
com `streamlit.testing.v1.AppTest`, o que mostra que testar a interface é viável e barato.

#### T-03 — Faltam testes de propriedade
**Sugestão** · testes

Testes com `hypothesis` (round-trip de unidades, invariância de escala de ρa, *fuzzing* do
`parse_number`) teriam pegado V-01 e V-02.

#### T-04 — CI limitada
**Média** · CI · `.github/workflows/ci.yml`

- Roda só em Python 3.11 no Ubuntu. A suíte passa em 3.13 localmente, mas 3.12 e 3.13 não são
  verificados, nem Windows e macOS (onde o comportamento de encoding do CSV importa).
- Não roda `mypy`, cobertura, `pip-audit` nem Dependabot.
- As actions estão fixadas por tag (`@v4`, `@v5`) e não por SHA. O risco é baixo, mas fixar
  por SHA é a prática recomendada.
- O `.gitignore` não ignora `.coverage` nem `htmlcov/`.

### 3.6 Segurança, privacidade e interoperabilidade

#### S-01 — Injeção de fórmula no CSV
**Média** (vira **Alta** quando houver importação ou compartilhamento de CSV) · segurança ·
`src/georesistivity/io.py:42, 64-66`

O campo livre "K source" é gravado no CSV sem tratamento:

```text
K source = =HYPERLINK("http://example.com","x")
CSV      -> 1,100.0,µV,...,"=HYPERLINK(""http://example.com"",""x"")",...
```

Excel e LibreOffice executam células que começam com `=`, `+`, `-` ou `@`. Hoje quem digita o
texto é o próprio usuário, mas os CSVs são compartilhados e a Fase 3 prevê importação.

**Correção:** prefixar com `'` os campos de texto que comecem com esses caracteres (seguindo a
recomendação da OWASP para *CSV injection*), só nas colunas de texto.

#### I-01 — O CSV não abre bem no Excel em português
**Média** · interoperabilidade · `src/georesistivity/io.py:64-66`, `app/app.py:178-186`

- Não há BOM UTF-8, e o Excel no Windows mostra `µV` como `Âµ` (verificado: o texto exportado
  não começa com BOM).
- O separador é `,` e o decimal é `.`. O Excel configurado em pt-BR espera `;` e `,`, então
  abre tudo numa única coluna.

**Correção:** oferecer dois dialetos na exportação, "padrão" (UTF-8, `,`, `.`) e "Excel
pt-BR" (UTF-8 com BOM, `;`, `,`).

#### S-02 — Telemetria do Streamlit ligada
**Baixa** · privacidade · raiz do repositório (falta `.streamlit/config.toml`)

`browser.gatherUsageStats` é `True` por padrão. Não há arquivo de configuração desligando a
coleta de uso.

**Correção:** criar `.streamlit/config.toml` com `gatherUsageStats = false`, junto com o
`toolbarMode` do item U-04.

#### S-03 — Documentos privados citados no `.gitignore`
**Verificar** · privacidade · `.gitignore:14-17`

O `.gitignore` lista `Relatorio final.docx`, `PlanoEstagio*.doc` e um `.txt` de anotações.
O zip atual **não** contém esses arquivos (verificado), mas o zip não traz o histórico. Se eles
foram commitados alguma vez e removidos depois, continuam acessíveis no histórico público do
GitHub. No clone original, verifique com:

```bash
git log --all --oneline -- "Relatorio final.docx" "PlanoEstagio*" "ajustar tamanho do grid do grafico .txt"
```

Se aparecer algum commit, o histórico precisa ser reescrito (`git filter-repo`). Isso é uma
ação destrutiva e deve ser feita por você.

#### S-04 — Sem lockfile para o aplicativo
**Sugestão** · reprodutibilidade · `pyproject.toml`

As dependências têm só limite inferior. Para a biblioteca isso é correto, mas o aplicativo
implantado deveria ter um lockfile (`uv lock` ou `pip-compile`) para builds reprodutíveis.

### 3.7 Código legado

#### L-01 — `legacy/` sem contexto e `buildozer.spec` com placeholders
**Sugestão** · documentação · `legacy/`

Os 8 protótipos documentam bem a evolução: média de 3 leituras, reset, reset do último valor,
gráfico, salvar PNG e app Kivy. Mas não há um `legacy/README.md` explicando a sequência. O
`buildozer.spec` tem valores de exemplo (`package.domain = org.test`, duplicado, e
`service = NameOfYourService`). O código legado não tem dados reais embutidos (verificado) e
já está fora do Ruff. Recomendo manter como está, com um README curto.

---

## 4. Pontos fortes (manter)

- Separação limpa entre o núcleo científico e a interface: o núcleo não importa Streamlit.
- Modelos imutáveis (`frozen=True, slots=True`) que preservam os valores originais e os
  convertidos lado a lado.
- Conversão de unidades explícita, com mensagens de erro que listam as unidades aceitas.
- Rejeição consistente de NaN, infinito, booleanos, corrente zero e K zero.
- A ordem de aquisição é preservada. A ordenação afeta só o gráfico, e isso é testado.
- A escala log-log não descarta pontos em silêncio: avisa quais linhas são incompatíveis.
- O "Clear all" pede confirmação.
- O README é honesto sobre as limitações científicas.
- 53 testes, 97% de cobertura, Ruff limpo e CI configurada.

---

## 5. Decisões que dependem do autor

| ID | Decisão | Recomendação |
| --- | --- | --- |
| D-1 | Política para separador de milhar ambíguo (V-01) | Preferência explícita de formato numérico (pt-BR por padrão) **e** rejeição de padrões ambíguos com mensagem orientando o usuário. |
| D-2 | Política de sinais (C-01) | Rejeitar K ≤ 0 e AB/2 ≤ 0. Aceitar ΔV e I negativos, com aviso quando ρa < 0. Isso muda um teste existente, de forma justificada. |
| D-3 | Licença (Q-03) | MIT ou BSD-3-Clause para máxima adoção acadêmica. GPL-3.0 se a intenção for exigir que derivados permaneçam abertos. |
| D-4 | Formato de exibição de ρa (C-04) | 4 dígitos significativos, com a localidade de D-1. |
| D-5 | Verificar o histórico do GitHub (S-03) | Rodar o comando de S-03 no clone original. |

---

## 6. Proposta de escopo para a Fase 2

Agrupando os achados em commits pequenos:

1. `fix(validation)`: V-01 (conforme D-1), V-02 e V-03.
2. `fix(core)`: C-01 (conforme D-2), C-02 e C-03.
3. `fix(io)`: S-01 e I-01.
4. `fix(app)`: U-01, U-02 (parte de limpeza e aviso de duplicata), U-04 (configuração),
   U-06, U-07, C-04.
5. `refactor`: Q-01, Q-05 e `py.typed`.
6. `build`: Q-02, Q-03 (conforme D-3), Q-04 e `.streamlit/config.toml` (S-02).
7. `test`: T-01, T-02 (AppTest), T-03 (hypothesis).
8. `ci`: T-04, `.gitignore`.
9. `docs`: README atualizado e `CHANGELOG.md` (0.2.0).

Ficam para a Fase 3: U-03 (persistência), U-05 (i18n), C-05 (MN/2 e metadados), C-06 (curva
por segmento), C-07 (média de leituras e exportação de figura) e C-08.

---

## Apêndice — como reproduzir

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]" pytest-cov mypy pandas-stubs hypothesis pip-audit
python -m pytest -q --cov=georesistivity --cov-report=term-missing
python -m mypy --strict src app
python -m pip_audit
python -c "from georesistivity import parse_number; print(parse_number('1,000'), parse_number('1_000'))"
```

Reprodução de V-01 na interface:

```python
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app/app.py")
at.run()
for i, v in enumerate(["125", "35", "1,000", "", ""]):
    at.text_input[i].set_value(v)
at.button[0].click().run()
print(at.metric[0].value)  # '3.57 ohm·m' — o valor pretendido era 3,571.43
```

---

## 7. Status após a Fase 2

Atualizado em 2026-10-22, versão `0.2.0`, branch `phase-2/hardening`. Decisões aplicadas:
D-1 (rejeitar números ambíguos e oferecer a preferência de formato, pt-BR por padrão),
D-2 (rejeitar K ≤ 0 e AB/2 ≤ 0 e avisar quando ρa < 0), D-3 (licença MIT) e D-4 (4 dígitos
significativos).

| Verificação | Antes | Depois |
| --- | --- | --- |
| Testes | 53 | 187 (inclui 15 de interface e 10 de propriedade) |
| Cobertura | 97% (linhas, só o núcleo) | 97,8% (linhas e ramos, núcleo e interface; mínimo de 95% na CI) |
| `mypy --strict` | 2 erros | 0 |
| `import georesistivity` | ~450 ms | ~9 ms |
| CI | 3.11 / Ubuntu | 3.11–3.13 / Ubuntu, Windows e macOS, mais mypy e pip-audit |

| ID | Status | Observação |
| --- | --- | --- |
| V-01 | Corrigido | `1,000` e `3.134` geram `AmbiguousNumberError` com as duas grafias sugeridas. |
| V-02 | Corrigido | Gramática ASCII explícita. |
| V-03 | Corrigido | `μ` grego aceito; espaços em volta da unidade são ignorados. |
| C-01 | Corrigido | Conforme D-2. |
| C-02 | Corrigido | Overflow e underflow na conversão são rejeitados. |
| C-03 | Corrigido | Conversão por deslocamento decimal exato: 0 divergências em 12 000 valores testados. |
| C-04 | Corrigido | Conforme D-1 e D-4. |
| C-05 | Fase 3 | MN/2, data e hora e identificação da estação. |
| C-06 | Fase 3 | Depende de MN/2. |
| C-07 | Fase 3 | Média de leituras e exportação de figura. |
| C-08 | Fase 3 | Depende do cálculo de K. |
| U-01 | Corrigido | Todos os campos inválidos são listados com o nome. |
| U-02 | Parcial | Limpeza dos campos e aviso de duplicata feitos. Editar ou excluir qualquer linha fica para a Fase 3. |
| U-03 | Fase 3 | Persistência. |
| U-04 | Parcial | A barra lateral e a barra de ferramentas foram corrigidas. O teclado numérico depende da arquitetura da Fase 3. |
| U-05 | Fase 3 | Só o formato numérico pt-BR foi feito agora; os textos continuam em inglês. |
| U-06 | Corrigido | `Ω·m` na interface e no gráfico. O CSV mantém `ohm.m` em ASCII. |
| U-07 | Corrigido | |
| Q-01 | Corrigido | |
| Q-02 | Corrigido | Distribuição renomeada para `georesistivity`; Streamlit virou o extra `[app]`. |
| Q-03 | Corrigido | MIT. |
| Q-04 | Corrigido | Importação tardia. |
| Q-05 | Corrigido | |
| T-01 | Corrigido | |
| T-02 | Corrigido | `tests/test_app.py`. |
| T-03 | Corrigido | `tests/test_properties.py`. |
| T-04 | Corrigido | Actions fixadas por SHA, Dependabot e pre-commit. |
| S-01 | Corrigido | |
| I-01 | Corrigido | Dialeto `excel-pt-br`. |
| S-02 | Corrigido | `.streamlit/config.toml`. |
| S-03 | Pendente (autor) | Rodar o comando da seção S-03 no clone original. |
| S-04 | Fase 3 | Lockfile junto com a decisão de distribuição do app. |
| L-01 | Pendente | Sugestão fora do escopo da Fase 2. |
