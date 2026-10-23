"""Textos da interface em português do Brasil."""

TEXT: dict[str, str] = {
    # Aplicativo e abas.
    "app.subtitle": "Calculadora de Resistividade Aparente",
    "app.intro": (
        "Calcule e registre a resistividade aparente a partir da diferença de potencial e da "
        "corrente medidas, com o fator geométrico informado ou calculado pela geometria."
    ),
    "tab.sheet": "Folha de campo (SEV)",
    "tab.single": "Medição avulsa",
    "tab.import": "Importar CSV",
    "common.cancel": "Cancelar",
    # Barra lateral.
    "sidebar.caption": "Ambiente de cálculo científico",
    "sidebar.preferences": "Preferências",
    "sidebar.language": "Idioma",
    "sidebar.number_format": "Formato numérico",
    "sidebar.number_format_help": (
        "Usado para exibir os resultados. A entrada aceita vírgula ou ponto como separador "
        "decimal; separador de milhar não é aceito."
    ),
    "sidebar.csv_format": "Formato do CSV exportado",
    "csv.standard": "Padrão (vírgula, ponto decimal)",
    "csv.excel_pt_br": "Excel pt-BR (ponto e vírgula, vírgula decimal)",
    "sidebar.about": "Sobre",
    "sidebar.about_text": (
        "Software para medições de resistividade aparente e sondagens elétricas verticais "
        "Schlumberger, no campo e no escritório."
    ),
    "sidebar.basis": "Base científica",
    "sidebar.basis_terms": (
        "- $\\rho_a$: resistividade aparente [Ω·m]\n"
        "- $K$: fator geométrico [m]\n"
        "- $\\Delta V$: diferença de potencial [V]\n"
        "- $I$: corrente injetada [A]"
    ),
    "sidebar.k_info": (
        "K pode ser informado diretamente ou calculado para o arranjo Schlumberger a partir de "
        "AB/2 e MN, com a fórmula exata. A calculadora de K cobre Wenner, dipolo-dipolo, "
        "polo-dipolo e qualquer arranjo de quatro eletrodos."
    ),
    "sidebar.units": "Unidades internas",
    "sidebar.units_text": "Tensão: **V**  \nCorrente: **A**  \nComprimento: **m**",
    "sidebar.disclaimer": (
        "Este aplicativo se destina a fins educacionais, de pesquisa e de computação "
        "científica. A interpretação de dados de resistividade elétrica exige conhecimento da "
        "geometria de aquisição e do contexto geológico."
    ),
    # Nomes de campos usados nas mensagens.
    "field.delta_v": "ΔV",
    "field.current": "Corrente",
    "field.geometric_factor": "Fator geométrico K",
    "field.spacing_ab2": "AB/2",
    "field.mn": "MN",
    # Formulário de medição avulsa.
    "form.title": "Entrada da medição",
    "form.k_mode": "Fator geométrico K",
    "form.k_mode_external": "Informar K",
    "form.k_mode_schlumberger": "Calcular K (Schlumberger)",
    "form.delta_v": "ΔV",
    "form.delta_v_placeholder": "ex.: 120,5",
    "form.voltage_unit": "Unidade de ΔV",
    "form.current": "Corrente",
    "form.current_placeholder": "ex.: 20",
    "form.current_unit": "Unidade da corrente",
    "form.k": "Fator geométrico K",
    "form.k_placeholder": "ex.: 5,89",
    "form.k_unit": "Unidade de K",
    "form.ab2": "AB/2",
    "form.ab2_optional": "AB/2 — opcional",
    "form.ab2_placeholder": "ex.: 20",
    "form.ab2_placeholder_optional": "Deixe em branco se não souber",
    "form.spacing_unit": "Unidade do espaçamento",
    "form.mn": "MN — distância total entre M e N",
    "form.mn_optional": "MN — opcional",
    "form.mn_placeholder": "ex.: 2",
    "form.mn_unit": "Unidade de MN",
    "form.formula_caption": (
        "Fórmula exata de Schlumberger. MN é a distância total entre M e N, como na folha de "
        "campo. A origem do K é registrada automaticamente."
    ),
    "form.source": "Origem do fator geométrico — opcional",
    "form.source_placeholder": "ex.: equipamento, tabela, folha de campo",
    "form.submit": "Calcular e adicionar medição",
    "form.not_added": "A medição não foi adicionada.",
    "form.added": "Medição nº {number} adicionada.",
    "form.duplicate": (
        "Esta medição é idêntica à nº {number}. Se não for uma leitura repetida de propósito, "
        "remova-a com '{remove}'."
    ),
    # Último resultado.
    "result.title": "Último resultado",
    "result.metric": "Resistividade aparente",
    "result.converted": "Valores convertidos",
    "result.k_source": "Origem do K: {source}",
    # Calculadora de K.
    "kcalc.title": "Calculadora de K",
    "kcalc.array": "Arranjo",
    "kcalc.length_unit": "Unidade de comprimento",
    "kcalc.submit": "Calcular K",
    "kcalc.hint": "Para usar, escolha '{enter_k}' e digite este valor com a unidade m.",
    "kcalc.failed": "Não foi possível calcular K.",
    "kcalc.failed_error": "Não foi possível calcular K: {error}",
    "array.schlumberger": "Schlumberger",
    "array.wenner": "Wenner-α",
    "array.dipole-dipole": "Dipolo-dipolo",
    "array.pole-dipole": "Polo-dipolo (B remoto)",
    "array.general": "Quatro eletrodos (geral)",
    "param.ab2": "AB/2",
    "param.mn": "MN (distância total)",
    "param.a": "a (espaçamento)",
    "param.n": "n (adimensional)",
    "param.am": "AM",
    "param.bm": "BM",
    "param.an": "AN",
    "param.bn": "BN",
    # Medições da sessão.
    "session.title": "Medições da sessão",
    "session.count.one": "{n} medição nesta sessão.",
    "session.count.other": "{n} medições nesta sessão.",
    "session.empty": "Nenhuma medição foi adicionada ainda.",
    "session.remove_last": "Remover a última medição",
    "session.clear_all": "Apagar todas as medições",
    "session.export": "Exportar CSV",
    "session.clear_question": "Apagar todas as medições desta sessão?",
    "session.clear_confirm": "Confirmar e apagar",
    # Tabela de medições avulsas (títulos na tela; o cabeçalho do CSV continua em inglês).
    "table.#": "nº",
    "table.Delta V": "ΔV",
    "table.Voltage unit": "Unidade de ΔV",
    "table.Current": "Corrente",
    "table.Current unit": "Unidade da corrente",
    "table.K": "K",
    "table.K unit": "Unidade de K",
    "table.K source": "Origem do K",
    "table.AB/2": "AB/2",
    "table.Spacing unit": "Unidade de AB/2",
    "table.MN": "MN",
    "table.MN unit": "Unidade de MN",
    "table.Delta V [V]": "ΔV [V]",
    "table.I [A]": "I [A]",
    "table.K [m]": "K [m]",
    "table.AB/2 [m]": "AB/2 [m]",
    "table.MN [m]": "MN [m]",
    "table.rho_a [ohm.m]": "ρa [Ω·m]",
    "table.Warnings": "Avisos",
    # Gráfico das medições avulsas.
    "plot.need_two": "Informe AB/2 em pelo menos duas medições para ver o gráfico.",
    "plot.title": "Gráfico por espaçamento",
    "plot.sort": "Ordenar por AB/2 no gráfico",
    "plot.scale": "Escala",
    "plot.linear": "Linear",
    "plot.loglog": "Log-log",
    "plot.log_incompatible": (
        "A escala log-log exige AB/2 e resistividade aparente positivos. Estas linhas da "
        "aquisição não podem ser representadas: {rows}. Nenhum ponto foi removido."
    ),
    "plot.sorted_caption": "O gráfico está ordenado por AB/2; a tabela segue a ordem de aquisição.",
    # Figuras.
    "figure.spacing_title": "Resistividade aparente × espaçamento dos eletrodos",
    "figure.sounding_title": "Sondagem elétrica vertical (Schlumberger)",
    "figure.ab2_axis": "AB/2 [m]",
    "figure.rho_axis": "Resistividade aparente [Ω·m]",
    "figure.mn_legend": "MN = {mn} m",
    "figure.quality_warning": "Aviso de qualidade",
    "figure.error_bars": "±1 erro-padrão da média (n ≥ 2)",
    "figure.survey_number": "SEV {number}",
    "figure.date_format": "%d/%m/%Y",
    # Relatório.
    "report.title": "Relatório de sondagem elétrica vertical (Schlumberger)",
    "report.details": "Dados do levantamento e da aquisição",
    "report.array": "Arranjo",
    "report.array_schlumberger": "Schlumberger (MN é a distância total entre M e N)",
    "report.units": "Unidades de ΔV / I",
    "report.cv_limit": "Limite de CV",
    "report.estimator": "Estimador",
    "report.estimator_mean": "média de ΔV/I das leituras não excluídas",
    "report.coordinates": "Coordenadas ({crs})",
    "report.summary": "Resumo",
    "report.summary_counts": "{positions} em {spacings}: {used} e {excluded}.",
    "count.reading_used.one": "{n} leitura usada",
    "count.reading_used.other": "{n} leituras usadas",
    "count.reading_excluded.one": "{n} excluída",
    "count.reading_excluded.other": "{n} excluídas",
    "report.summary_range": "AB/2 de {ab2_min} a {ab2_max} m; ρa de {rho_min} a {rho_max} Ω·m.",
    "report.summary_warnings.one": "{n} posição com aviso de qualidade.",
    "report.summary_warnings.other": "{n} posições com aviso de qualidade.",
    "report.summary_unused.one": "{n} linha da folha não foi usada (veja abaixo).",
    "report.summary_unused.other": "{n} linhas da folha não foram usadas (veja abaixo).",
    "report.summary_empty": "A folha ainda não tem leituras completas.",
    "report.curve": "Curva de SEV",
    "report.no_curve": "Nenhuma posição tem ρa positivo, então não há curva.",
    "report.points": "Posições",
    "report.readings": "Leituras",
    "report.col_delta_v": "ΔV [{unit}]",
    "report.col_current": "I [{unit}]",
    "report.col_r": "R [Ω]",
    "report.col_rho": "ρa [Ω·m]",
    "report.col_excluded": "Excluída",
    "report.col_reason": "Motivo",
    "report.col_entered": "Digitado em",
    "report.unused": "Linhas da folha não usadas",
    "report.col_row": "Linha",
    "report.col_problem": "Motivo",
    "report.waiting": "{column}: ainda não digitado",
    "report.warnings": "Avisos de qualidade",
    "report.col_warning": "Aviso",
    "report.col_meaning": "Significado",
    "report.col_positions": "Posições",
    "report.history": "Histórico de alterações",
    "report.no_history": "Nenhuma alteração registrada.",
    "report.empty_table": "Nenhuma.",
    "report.methods": "Métodos",
    "report.method_k": (
        "Fator geométrico Schlumberger exato: K = π (L² − l²) / (2 l), com L = AB/2 e l = MN/2, "
        "em metros."
    ),
    "report.method_rho": (
        "Resistividade aparente: ρa = K · média(ΔV_i / I_i) sobre as leituras não excluídas "
        "da posição, em Ω·m; cada leitura tem o mesmo peso."
    ),
    "report.method_se": (
        "Erro-padrão de ρa: K · s / √n, com s o desvio-padrão amostral de ΔV_i / I_i; só existe "
        "com n ≥ 2 e é o tamanho das barras de erro. CV = s / |média|, com aviso acima de "
        "{cv_limit}%."
    ),
    "report.method_wide_mn": (
        "Aviso de MN largo quando (AB/2) / (MN/2) < 4; o K continua exato para qualquer MN menor "
        "que AB."
    ),
    "report.method_entered": (
        '"Digitado em" é o momento em que ΔV e I da linha ficaram completos na folha digital. '
        "Quando uma folha de papel é passada a limpo, é o horário da digitação, não o da medição."
    ),
    "report.method_recomputed": (
        "Os valores calculados não são gravados no projeto: este relatório os recalcula a "
        "partir dos valores digitados, nas unidades indicadas."
    ),
    "report.references": "Referências",
    "report.footer": "GeoResistivity {version} · gerado em {time} · SHA-256 do projeto: {digest}",
    "report.page": "Página {page} de {pages}",
    "report.format": "Formato do relatório",
    "report.download": "Baixar relatório ({format})",
    "report.panel": "Relatório da SEV",
    "report.panel_caption": (
        "Cabeçalho, curva, posições, leituras com exclusões, linhas não usadas, avisos, "
        "histórico e métodos, no idioma e no formato numérico escolhidos."
    ),
    # Histórico de alterações.
    "history.title": "Histórico de alterações",
    "history.count.one": "{n} alteração registrada.",
    "history.count.other": "{n} alterações registradas.",
    "history.empty": (
        "Nenhuma alteração registrada. Digitar numa célula vazia não conta; corrigir ou apagar "
        "um valor já digitado, apagar uma linha, trocar a folha ou as unidades conta, com horário."
    ),
    "history.undo": "Desfazer última alteração",
    "history.next_undo": "Desfazer reverte: {change}",
    "history.nothing_to_undo": "Todas as alterações já foram desfeitas.",
    "history.filter": "Mostrar",
    "history.all_rows": "Todas as alterações",
    "history.row_option": "Linha {number}: AB/2 {ab2}, MN {mn}",
    "history.deleted_row_option": "Linha apagada: AB/2 {ab2}, MN {mn}",
    "history.row_number_option": "Linha {number} (fora da folha atual)",
    "history.col_number": "Nº",
    "history.col_time": "Horário",
    "history.col_row": "Linha",
    "history.col_change": "Alteração",
    "history.time_format": "%d/%m/%Y %H:%M:%S",
    "history.edit": "{field}: {old} → {new}",
    "history.empty_value": "(vazio)",
    "history.yes": "sim",
    "history.no": "não",
    "history.delete_row": "Linha apagada ({summary})",
    "history.replace_import": "Folha substituída pela importação de {detail}",
    "history.replace_new_sheet": "Folha substituída por uma folha nova",
    "history.replace_template": "Folha substituída pelo modelo {detail}",
    "history.append_rows": "{rows} acrescentadas pela importação de {detail}",
    "history.units": "Unidades de ΔV / I: {old} → {new}",
    "history.undo_entry": "Desfeito o registro nº {number}",
    "history.undone": "{change} (desfeita)",
    "history.export": "Exportar histórico (CSV)",
    "history.field_marker": "Cor",
    "history.field_ab2": "AB/2",
    "history.field_mn": "MN",
    "history.field_delta_v": "ΔV",
    "history.field_current": "I",
    "history.field_excluded": "Excluir",
    "history.field_reason": "Motivo da exclusão",
    # Exportação da figura.
    "export.title": "Exportar figura",
    "export.format": "Formato",
    "export.format_png": "PNG (imagem, 300 dpi)",
    "export.format_svg": "SVG (vetorial, editável)",
    "export.format_pdf": "PDF (vetorial, para imprimir)",
    "export.size": "Tamanho",
    "export.size_standard": "Padrão (17,8 × 17,8 cm)",
    "export.size_scale": "Escala do papel bilog",
    "export.decade_mm": "Módulo [mm por década]",
    "export.decade_help": (
        "Tamanho de uma década nos dois eixos, como no papel bilog e nas curvas-padrão. O "
        "padrão de {default} mm é provisório: troque pelo módulo do seu papel."
    ),
    "export.scale_caption": (
        "Área do gráfico: {width} × {height} cm ({x_decades} × {y_decades} décadas). Para "
        "manter a escala, imprima em 100% (sem ajustar à página) e confira uma década com a "
        "régua; o PDF e o SVG guardam o tamanho exato."
    ),
    "export.title_with_survey": "Título com SEV nº, local e data",
    "export.download": "Baixar figura ({format})",
    # Avisos de qualidade.
    "warning.negative_apparent_resistivity": (
        "Resistividade aparente negativa. Verifique a polaridade dos eletrodos de potencial, o "
        "sentido da corrente e as conexões dos cabos."
    ),
    "warning.schlumberger_wide_mn": (
        "MN está largo para este AB/2: (AB/2)/(MN/2) ficou abaixo de 4. O K usa a fórmula "
        "exata e continua correto, mas a leitura faz a média do potencial num intervalo largo; "
        "considere um MN menor neste espaçamento."
    ),
    "warning.stack_high_variation": (
        "As leituras repetidas variam mais do que o limite do coeficiente de variação."
    ),
    "warning.stack_mixed_signs": "As leituras repetidas têm valores positivos e negativos.",
    "warning_short.negative_apparent_resistivity": "ρa negativo",
    "warning_short.schlumberger_wide_mn": "MN largo",
    "warning_short.stack_high_variation": "CV acima do limite",
    "warning_short.stack_mixed_signs": "sinais trocados",
    # Folha de campo.
    "sheet.title": "Folha de campo Schlumberger",
    "sheet.caption": (
        "Digite ΔV e I nas linhas medidas; linhas em branco são ignoradas. Uma segunda linha "
        "com o mesmo AB/2 e o próximo MN é uma leitura de superposição. Acrescente uma linha "
        "com o mesmo AB/2 e MN para registrar uma leitura repetida. O K usa a fórmula exata, "
        "com MN como a distância total entre M e N. A folha é salva automaticamente neste "
        "computador; use Salvar projeto na barra lateral para guardar um arquivo."
    ),
    "sheet.dv_unit": "Unidade de ΔV",
    "sheet.i_unit": "Unidade de I",
    "sheet.cv_limit": "Limite de CV [%]",
    "sheet.cv_help": (
        "Leituras repetidas de uma posição com coeficiente de variação acima deste limite são "
        "sinalizadas."
    ),
    "sheet.col_marker": "Cor",
    "sheet.col_marker_help": "Cor de marcação do cabo ou carretel para este AB/2",
    "sheet.col_ab2": "AB/2 [m]",
    "sheet.col_mn": "MN [m]",
    "sheet.col_mn_help": "Distância total entre M e N",
    "sheet.col_delta_v": "ΔV [{unit}]",
    "sheet.col_current": "I [{unit}]",
    "sheet.col_exclude": "Excluir",
    "sheet.col_reason": "Motivo da exclusão",
    "sheet.issue_ab2": "AB/2",
    "sheet.issue_mn": "MN",
    "sheet.issue_delta_v": "ΔV",
    "sheet.issue_current": "I",
    "sheet.issue_reason": "Motivo da exclusão",
    "sheet.waiting": "Aguardando valor em {rows}.",
    "sheet.waiting_row": "linha {number} ({column})",
    "sheet.not_used": "Estas linhas não foram usadas:",
    "sheet.row_issue": "**Linha {number}** — {details}",
    "sheet.empty": "Digite ΔV e I em uma linha para ver o resultado e a curva.",
    "sheet.summary.one": "{positions} medida em {spacings}.",
    "sheet.summary.other": "{positions} medidas em {spacings}.",
    "sheet.error_bars": "Barras de erro (±1 erro-padrão)",
    "sheet.error_bars_help": (
        "Erro-padrão da média de ΔV/I multiplicado por K (K·s/√n). Só existe nas posições "
        "com duas ou mais leituras válidas. Se a barra passar de zero, a parte de baixo é "
        "pontilhada até a borda do gráfico."
    ),
    "sheet.error_bars_on.one": (
        "Barra de erro em {with_bars} de {positions} da curva "
        "(só onde há duas ou mais leituras válidas)."
    ),
    "sheet.error_bars_on.other": (
        "Barras de erro em {with_bars} de {positions} da curva "
        "(só onde há duas ou mais leituras válidas)."
    ),
    "sheet.error_bars_none": (
        "Nenhuma posição tem duas ou mais leituras válidas, então a curva não tem barras de erro."
    ),
    "sheet.not_on_curve": "Fora da curva log-log porque ρa não é positivo: {positions}.",
    "sheet.position": "AB/2 = {ab2} m (MN = {mn} m)",
    "sheet.export_points": "Exportar pontos (CSV)",
    "sheet.export_readings": "Exportar leituras (CSV)",
    "points.ab2": "AB/2 [m]",
    "points.mn": "MN [m]",
    "points.marker": "Cor",
    "points.k": "K [m]",
    "points.readings": "Leituras",
    "points.readings_excluded": "{used} (+{excluded} excluídas)",
    "points.rho": "ρa [Ω·m]",
    "points.se": "Erro-padrão ρa [Ω·m]",
    "points.cv": "CV [%]",
    "points.warnings": "Avisos",
    # Modelos e nova folha.
    "templates.title": "Nova folha e modelos",
    "templates.layout": "Modelo para uma nova folha",
    "templates.standard": "Folha de campo padrão (45 posições)",
    "templates.new": "Nova folha",
    "templates.new_question": (
        "Começar uma nova folha? Tudo o que foi digitado nesta folha será descartado."
    ),
    "templates.new_confirm": "Descartar e começar nova folha",
    "templates.caption": (
        "Salve AB/2, MN e as cores de marcação desta folha como modelo, sem as leituras, para "
        "começar novas folhas com eles."
    ),
    "templates.name": "Nome do modelo",
    "templates.save": "Salvar modelo",
    "templates.saved": "Modelo '{name}' salvo em {folder}.",
    "templates.not_saved": "O modelo não foi salvo: {error}",
    # Dados do levantamento.
    "survey.title": "Dados do levantamento",
    "survey.name": "Nome do levantamento",
    "survey.sev": "SEV nº",
    "survey.date": "Data",
    "survey.area": "Área",
    "survey.place": "Local",
    "survey.operator": "Operador",
    "survey.equipment": "Equipamento",
    "survey.azimuth": "Azimute de AB [°]",
    "survey.azimuth_help": (
        "Direção da linha dos eletrodos de corrente, em graus a partir do norte."
    ),
    "survey.latitude": "Latitude [°]",
    "survey.latitude_help": "Graus decimais WGS 84; negativa ao sul do equador.",
    "survey.longitude": "Longitude [°]",
    "survey.longitude_help": "Graus decimais WGS 84; negativa a oeste de Greenwich.",
    "survey.notes": "Observações",
    # Projeto, salvamento automático e recuperação.
    "project.title": "Projeto",
    "project.open": "Abrir projeto",
    "project.open_help": (
        "Um arquivo .geores.json salvo pelo GeoResistivity. Ele substitui a folha atual, os "
        "dados do levantamento e as medições avulsas."
    ),
    "project.save": "Salvar projeto",
    "project.opened": "{source} aberto.",
    "project.open_failed": "Não foi possível abrir {source}: {error}",
    "project.not_utf8": "Não foi possível abrir {name}: o texto não está em UTF-8.",
    "project.autosave_source": "A cópia salva automaticamente",
    "project.read_failed": "Não foi possível ler a cópia salva automaticamente: {error}",
    "autosave.off": "O salvamento automático está desligado nesta instalação.",
    "autosave.failed": "O salvamento automático falhou: {error}. Salve o arquivo do projeto.",
    "autosave.done": "Salvo automaticamente às {time} em {folder}.",
    "autosave.pending": (
        "O salvamento automático começa com o primeiro valor digitado, em {folder}."
    ),
    "recovery.info": (
        "Há trabalho de uma sessão anterior salvo automaticamente. Restaure para continuar."
    ),
    "recovery.untitled": "Sem título",
    "recovery.sev": "SEV {number}",
    "recovery.restore": "Restaurar",
    # Importação de CSV.
    "import.title": "Importar CSV",
    "import.caption": (
        "Importe leituras para a folha de campo, ou medições avulsas, a partir de um arquivo "
        "CSV, inclusive os arquivos exportados pelo GeoResistivity (padrão ou Excel pt-BR). As "
        "linhas com problema são listadas e ficam de fora."
    ),
    "import.file": "Arquivo CSV",
    "import.separator": "Separador",
    "import.separator_auto": "Detectar",
    "import.separator_semicolon": "Ponto e vírgula ;",
    "import.separator_comma": "Vírgula ,",
    "import.separator_tab": "Tabulação",
    "import.read_as": "{name}: {encoding}, {separator}, {rows}.",
    "import.first_rows": "Primeiras {shown} de {rows}.",
    "import.no_name": "(sem nome)",
    "import.target": "Importar para",
    "import.target_sheet": "Folha de campo (leituras por AB/2 e MN)",
    "import.target_measurements": "Medições avulsas (com K)",
    "import.columns": "Colunas",
    "import.not_in_file": "— não está no arquivo —",
    "import.decimal": "Separador decimal do arquivo",
    "import.decimal_auto": "Detectar pelos números ({detected})",
    "import.decimal_point": "Ponto (1.5)",
    "import.decimal_comma": "Vírgula (1,5)",
    "import.decimal_strict": "Indefinido: recusar valores como 1,000",
    "import.units": "Unidades das colunas sem coluna de unidade",
    "import.length_unit": "Unidade de comprimento (K, AB/2, MN)",
    "import.choose_columns": "Escolha uma coluna para: {fields}.",
    "import.ready.one": "{ready} de {rows} pronta para importar.",
    "import.ready.other": "{ready} de {rows} prontas para importar.",
    "import.problems": "{problems}; estas linhas ficarão de fora:",
    "import.units_caption": "ΔV em {voltage}, I em {current}; comprimentos em metros.",
    "import.how": "Como",
    "import.replace": "Substituir a folha de campo",
    "import.append": "Acrescentar depois das linhas atuais",
    "import.button": "Importar {rows}",
    "import.done_sheet.one": "{rows} de {name} importada para a aba Folha de campo.",
    "import.done_sheet.other": "{rows} de {name} importadas para a aba Folha de campo.",
    "import.done_measurements.one": "{measurements} de {name} importada para Medição avulsa.",
    "import.done_measurements.other": "{measurements} de {name} importadas para Medição avulsa.",
    "import.nothing": "Nada foi importado: {error}",
    "import.units_differ": "Nada foi importado: as unidades são diferentes das da folha.",
    "import.unreadable": "Não foi possível ler o arquivo: {error}",
    "import.issue_line": "Linha",
    "import.issue_column": "Coluna",
    "import.issue_problem": "Problema",
    "importfield.ab2": "AB/2 [m]",
    "importfield.mn": "MN [m]",
    "importfield.delta_v": "ΔV",
    "importfield.current": "I",
    "importfield.voltage_unit": "Unidade de ΔV",
    "importfield.current_unit": "Unidade de I",
    "importfield.marker": "Cor",
    "importfield.excluded": "Excluída",
    "importfield.reason": "Motivo da exclusão",
    "importfield.geometric_factor": "K",
    "importfield.geometric_factor_unit": "Unidade de K",
    "importfield.spacing_ab2": "AB/2",
    "importfield.spacing_unit": "Unidade de AB/2",
    "importfield.mn_unit": "Unidade de MN",
    "importfield.source": "Origem do K",
    # Contagens.
    "count.row.one": "{n} linha",
    "count.row.other": "{n} linhas",
    "count.data_row.one": "{n} linha de dados",
    "count.data_row.other": "{n} linhas de dados",
    "count.problem.one": "{n} problema",
    "count.problem.other": "{n} problemas",
    "count.measurement.one": "{n} medição",
    "count.measurement.other": "{n} medições",
    "count.position.one": "{n} posição",
    "count.position.other": "{n} posições",
    "count.spacing.one": "{n} espaçamento AB/2",
    "count.spacing.other": "{n} espaçamentos AB/2",
    "count.reading.one": "{n} leitura",
    "count.reading.other": "{n} leituras",
}

# Mensagens do núcleo científico, pelos mesmos códigos de georesistivity.messages.EN.
PROBLEMS: dict[str, str] = {
    "text.raw": "{text}",
    "number.empty": "o valor não pode ficar vazio",
    "number.both_separators": (
        "separadores decimais ambíguos; separador de milhar não é aceito (digite 1234,5 ou 1234.5)"
    ),
    "number.ambiguous": (
        "valor ambíguo {value!r}: {separator!r} pode ser separador de milhar ou decimal. "
        "Digite {integer} para o número inteiro, ou {decimal} para o valor decimal"
    ),
    "number.invalid": "valor numérico inválido: {value!r}",
    "number.not_finite": "o valor precisa ser finito",
    "number.wrong_separator": (
        "{value!r} usa {other!r}, mas o separador decimal é {separator!r}; separador de milhar "
        "não é aceito"
    ),
    "value.named_not_finite": "{name} precisa ser finito",
    "unit.missing": "falta a unidade em {text!r}; escreva como 20m ou 125mV",
    "voltage.unsupported_unit": (
        "unidade de tensão não suportada {unit!r}; unidades aceitas: {supported}"
    ),
    "current.unsupported_unit": (
        "unidade de corrente não suportada {unit!r}; unidades aceitas: {supported}"
    ),
    "length.unsupported_unit": (
        "unidade de comprimento não suportada {unit!r}; unidades aceitas: {supported}"
    ),
    "voltage.too_large": "o valor de tensão é grande demais para converter ao SI",
    "current.too_large": "o valor de corrente é grande demais para converter ao SI",
    "length.too_large": "o valor de comprimento é grande demais para converter ao SI",
    "voltage.too_small": "o valor de tensão é pequeno demais para converter ao SI",
    "current.too_small": "o valor de corrente é pequeno demais para converter ao SI",
    "length.too_small": "o valor de comprimento é pequeno demais para converter ao SI",
    "core.current_zero": "a corrente não pode ser zero",
    "core.k_zero": "o fator geométrico não pode ser zero",
    "core.k_negative": "o fator geométrico precisa ser positivo",
    "core.result_not_finite": "o resultado da resistividade aparente precisa ser finito",
    "field.zero": "não pode ser zero",
    "field.not_positive": "precisa ser positivo",
    "field.not_finite": "precisa ser finito",
    "field.required": "é obrigatório",
    "field.required_for_k": "é obrigatório para calcular K",
    "geometry.mn_too_wide": "MN/2 precisa ser menor que AB/2",
    "geometry.too_large": "o fator geométrico é grande demais para representar",
    "geometry.undefined": "o arranjo de eletrodos não gera diferença de potencial; K é indefinido",
    "reading.reason_required": "uma leitura excluída precisa de motivo",
    "sheet.reason_required": "é obrigatório para excluir uma leitura",
    "sheet.not_typed": "ainda não digitado",
    "measurement.spacing_pair": "o valor e a unidade do espaçamento devem vir juntos",
    "measurement.mn_pair": "o valor e a unidade de MN devem vir juntos",
    "csv.bad_utf8": "o arquivo começa como UTF-8, mas não é UTF-8 válido",
    "csv.invalid": "o arquivo não é um CSV válido (linha {line}): {detail}",
    "csv.no_header": "o arquivo não tem linha de cabeçalho",
    "csv.not_flag": "{text!r} não é sim ou não",
    "csv.unit_differs": "{text!r} é diferente de {unit!r}, usado nas outras linhas",
    "csv.other_value_filled": "está vazio, mas o outro valor está preenchido",
    "project.invalid_json": "não é um JSON válido (linha {line}, coluna {column})",
    "project.not_project": "não é um projeto do GeoResistivity (esperado {expected!r})",
    "project.bad_version": "precisa ser um número inteiro positivo",
    "project.newer_version": (
        "o arquivo usa a versão {version}, mais nova do que este programa aceita "
        "({supported}); atualize o GeoResistivity para abri-lo"
    ),
    "project.must_be_object": "precisa ser um objeto",
    "project.must_be_list": "precisa ser uma lista",
    "project.must_be_text": "precisa ser texto",
    "project.must_be_number": "precisa ser um número",
    "project.must_be_number_or_null": "precisa ser um número ou null",
    "project.must_be_flag": "precisa ser true ou false",
    "project.unknown_field": "campo desconhecido",
    "project.required": "é obrigatório",
    "project.array": "só o arranjo 'schlumberger' é aceito",
    "project.cv_limit": "precisa estar entre 0 e 100",
    "project.date": "precisa ser uma data no formato AAAA-MM-DD",
    "project.range": "{name} precisa estar entre {low:g} e {high:g}",
    "project.not_finite": "{name} precisa ser um número finito",
    "project.unsupported_voltage_unit": "unidade de ΔV não suportada na folha: {unit!r}",
    "project.unsupported_current_unit": "unidade de corrente não suportada na folha: {unit!r}",
    "project.cv_limit_shown": "o limite de CV precisa estar entre {low:g} e {high:g}%",
    "template.not_template": "não é um modelo de folha (esperado {expected!r})",
    "template.bad_version": "precisa ser {version}",
    "template.needs_name": "o modelo precisa de um nome",
    "template.needs_rows": "o modelo precisa de pelo menos uma linha",
    "figure.decade_mm": "o módulo deve estar entre {low:g} e {high:g} mm; foi {value:g}",
    "figure.nothing_to_plot": (
        "a folha de campo não tem posição com resistividade aparente positiva"
    ),
    "project.datetime": "deve ser data e hora com fuso, como 2026-10-22T09:14:00-03:00",
    "project.duplicate_row_id": "o identificador de linha {id!r} aparece em mais de uma linha",
    "project.choice": "deve ser um destes: {choices}",
    "project.entry_number": "deve ser o número de um registro anterior",
    "project.units_pair": "deve ser uma lista com a unidade de ΔV e a de corrente",
    "history.row_missing": "a linha desta alteração não está mais na folha",
    "template.layout_only": "o modelo guarda só cor, AB/2 e MN",
}
