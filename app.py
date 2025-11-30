import streamlit as st
import re
import datetime

# ==============================================================================
# CONFIGURAÇÕES E BANCO DE DADOS
# ==============================================================================

st.set_page_config(page_title="Gerador de Evolução UTI", page_icon="🏥", layout="wide")

# CSS para deixar o visual mais compacto (útil para celular)
st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 1rem;}
        h1 {font-size: 1.5rem;}
        h2 {font-size: 1.2rem;}
        .stTextArea textarea {font-size: 14px;}
    </style>
""", unsafe_allow_html=True)

# --- TERMOS E GATILHOS (Mesma lógica do Colab) ---
TERMOS_PROTEGIDOS = [
    "s/n", "S/N", "mg/dL", "g/dL", "U/L", "U/ml", "mcg/kg/min", "ml/h", 
    "ml/kg", "ml/kg/h", "L/min", "c/d", "s/d", "A/C", "P/F", "b/min", "bpm", 
    "24/24h", "12/12h", "AA", "PO", "SVD", "CN", "TOT", "TQT"
]

GATILHOS_CONDUTA = [
    "realizo", "realizado", "fiz", "feito", "solicito", "solicitado", "peço", 
    "inicio", "iniciado", "começo", "mantenho", "mantido", "suspendo", "suspenso", 
    "retiro", "retirado", "ajusto", "ajustado", "corrijo", "corrigido", "troco", 
    "trocado", "desligo", "desligado", "aumento", "aumentado", "reduzo", "reduzido", 
    "prescrevo", "prescrito", "instalo", "instalado", "passo", "passado", 
    "otimizo", "otimizado", "escalono", "escalonado", "descalono", "adiciono", "associo",
    "transiciono", "deambulou", "sedestrou", "desmamado", "exteriorizou", "reabordado"
]

MAPA_EXAMES_SISTEMA = {
    "RENAL":  {"Ureia": "Ur", "Creatinina": "Cr", "Sódio": "Na", "Potássio": "K", "Magnésio": "Mg", "Fósforo": "P", "Cálcio": "Ca", "Bicarbonato": "Bic"},
    "INFECTO": {"Leucograma": "Leucograma", "Hb": "Hb", "Ht": "Ht", "Plaquetas": "Plq", "PCR": "PCR", "Procalcitonina": "PCT", "INR": "INR"},
    "CARDIO": {"Lactato": "Lac", "Troponina": "Tropo", "CK-MB": "CKMB", "BNP": "BNP", "D-dímero": "D-dim", "SvO2": "SvO2", "GapCO2": "GapCO2"},
    "TGI":    {"TGO": "TGO", "TGP": "TGP", "GGT": "GGT", "FA": "FA", "Bilirrubinas": "BT", "Amilase": "Amil", "Lipase": "Lip"},
    "RESP":   {"pH": "pH", "pCO2": "pCO2", "pO2": "pO2", "SatO2": "Sat", "Rel. P/F": "P/F", "BE": "BE"}
}

SINONIMOS_BUSCA = {
    "Hb": ["hb", "hgb"], "Ht": ["ht", "hto"], "Leucograma": ["leuco", "leucocitos"],
    "Plaquetas": ["plq", "plaquetas"], "PCR": ["pcr"], "INR": ["inr"],
    "Ureia": ["ureia", "ur"], "Creatinina": ["cr", "creat"],
    "Sódio": ["sodio", "na"], "Potássio": ["potassio", "k"], "Magnésio": ["magnesio", "mg"],
    "Cálcio": ["calcio", "ca"], "Lactato": ["lactato", "lac"],
    "pH": ["ph"], "pCO2": ["pco2"], "pO2": ["po2"], "Bicarbonato": ["bic", "hco3"],
    "TGO": ["tgo", "ast"], "TGP": ["tgp", "alt"], "Bilirrubinas": ["bt", "bilirrubina total"]
}

DB_FRASES = {
    "CONTEXTO": [
        "PO imediato de {procedimento}, sem intercorrências",
        "PO tardio de {procedimento} ({data}), evoluindo estável",
        "Admissão na UTI pós {procedimento}",
        "Paciente em tratamento de Choque Séptico (Foco: {foco})",
        "Neurocrítico (HIC/AVE/TCE), medidas de neuroproteção",
        "Reabordado cirurgicamente em {data} para {procedimento}"
    ],
    "NEURO": [
        "RASS 0, vigil, colaborativo, orientado",
        "RASS -1 a -3, sonolento mas despertável ao chamado",
        "RASS -4/-5, comatoso / Agitado (RASS +)",
        "Sem sedação / Desligada sedação / Sedação suspensa",
        "Sedado com {drogas} (RASS {rass})",
        "Analgesia otimizada com {droga} / Necessitou ansiólise ({droga})",
        "Pupilas isocóricas / Anisocoria / Pupilas {tamanho}",
        "Sem déficits focais / Hemiparesia à {lado}",
        "Força muscular preservada / Diminuída em {loc} (Grau {grau})",
        "Reflexos de tronco preservados / Abolidos",
        "Sem crises convulsivas / Crises no período (cd: {conduta})",
        "Deambulou no período / Sedestrou / Restrito ao leito",
        "Sialorréico (medidas xerostômicas) / Higiene oral precária",
        "Com bom controle de tronco / Sem controle de tronco",
        "Delirium hiperativo (CAM-ICU+) / Hipoativo",
        "CPOT negativo / positivo | BPS negativo / positivo",
        "Disártrico / Afásico / Contactuante",
        "NIHSS {pts} pts ({detalhe})",
        "Sem sinais de encefalopatia / Com sinais de encefalopatia"
    ],
    "CARDIO": [
        "Hemodinâmica estável, sem drogas vasoativas (DVA)",
        "Instabilidade hemodinâmica / Choque",
        "Em uso de Noradrenalina {dose} mcg/kg/min",
        "Em desmame de DVA (Noradrenalina {dose})",
        "Desmamado vasodilatador, iniciado oral ({droga})",
        "Ritmo Sinusal / Fibrilação Atrial (FA)",
        "FA controlada com {droga} (FC {fc}bpm)",
        "Bem perfundido (TEC < 3s, Lac normal) / Má perfusão (TEC > 4s)",
        "Hipertenso, em uso de Nitroprussiato {vazao} ml/h",
        "Hipotenso, realizada expansão {quant} ml",
        "Extremidades quentes / Extremidades frias"
    ],
    "RESP": [
        "Eupneico em ar ambiente (AA), confortável",
        "Em uso de Cateter Nasal (CN) {litros} L/min",
        "Em Máscara de Venturi {perc}%",
        "VM via TOT, modo {modo} / VM via TQT",
        "Parâmetros: Vol {vol}ml, PEEP {peep}, FIO2 {fio}%",
        "Desconforto respiratório leve / moderado",
        "Em VNI intermitente ({motivo})",
        "Extubação realizada no período sem intercorrências",
        "Ausculta: Murmúrio vesicular presente / Creptos em {loc}",
        "Dreno de tórax à {lado} oscilante / Improdutivo",
        "TC de Tórax: {laudo}"
    ],
    "TGI": [
        "Dieta oral liberada e bem aceita / Aceitação parcial",
        "Dieta enteral via SNE/GTT a {vazao}ml/h",
        "Iniciado dieta enteral / Progressão de dieta",
        "Suspenso NPT, iniciado dieta enteral",
        "Dieta zero / Dieta suspensa por {motivo}",
        "Nutrição Parenteral Total (NPT) em curso",
        "Retirado SNG no período",
        "Abdome flácido, indolor / Globoso e distendido",
        "Evacuações presentes ({aspecto}) / Ausentes",
        "Glicemias controladas / Labéis (Iniciado Insulina)",
        "Em uso de procinéticos e IBP"
    ],
    "RENAL": [
        "Diurese espontânea conservada e clara",
        "Diurese via SVD, aspecto {aspecto}",
        "Diurese em baixo fluxo / Oligúria",
        "Realizado estímulo diurético (boa resposta / sem resposta)",
        "Função renal preservada / Função renal alterada (estável)",
        "Função renal em melhora / Função renal em piora",
        "Em Hemodiálise (HD) intermitente / Em CVVHD",
        "Sem DHE graves / Reposição de K/Mg",
        "Nefrostomia produtiva ({quant}ml) / improdutiva",
        "Balanço Hídrico negativo / BH positivo / BH neutro"
    ],
    "INFECTO": [
        "Afebril nas últimas 24h, curva térmica estável",
        "Subfebril no período / Picos febris isolados ({valor}ºC)",
        "Em uso de antibiótico: {atb} / Sem antibióticos",
        "Escalonado antibiótico para {novo} / Suspenso antibiótico",
        "Sem foco infeccioso aparente",
        "Curativos limpos e secos / Deiscência de ferida operatória",
        "Sem sinais flogísticos em acessos venosos",
        "Leucograma: estável / em melhora / com leucocitose",
        "Hb estável / Hb em queda"
    ],
    "GERAL": [
        "Retirado cateter / Trocado CVC / PAI / Sorensen",
        "Acesso com sinais de infecção / Sem sinais de infecção",
        "Presença de edema assimétrico / simétrico",
        "Curativo a vácuo / Curativo com {produto}",
        "Sem lesões de pele / Presença de LPP grau {grau} em {loc}",
        "Em uso de irrigação vesical contínua",
        "Sem exteriorização de sangramentos"
    ]
}

# ==============================================================================
# FUNÇÕES DE LÓGICA (CORE)
# ==============================================================================

def buscar_valor_antigo(texto, chave):
    if not texto: return None
    termos = SINONIMOS_BUSCA.get(chave, [chave.lower()])
    for t in termos:
        match = re.search(rf"\b{re.escape(t)}[:=]?\s+((?:\d+[.,]?\d*\s*)+)", texto.lower().replace(",", "."))
        if match:
            nums = [n for n in match.group(1).split() if n[0].isdigit()]
            return nums[-1] if nums else None
    return None

def processar_frase_ui(frase_base, complemento_usuario, dados_extra):
    """Processa a frase escolhida no UI com os dados e complementos"""
    frase = frase_base
    
    # Substituir placeholders de vitais
    for k, v in dados_extra.items():
        if f"{{{k}}}" in frase:
            if v: frase = frase.replace(f"{{{k}}}", v)
            else: frase = frase.replace(f"{{{k}}}", "")
            
    # Lógica de Barras /
    tem_barra = "/" in frase and not any(tp in frase for tp in TERMOS_PROTEGIDOS)
    
    # Se o usuário digitou complemento
    if complemento_usuario:
        # Se tem placeholder na frase, o complemento preenche ele
        if "{" in frase:
            # Encontra o primeiro placeholder
            inicio = frase.find("{")
            fim = frase.find("}")
            if inicio != -1 and fim != -1:
                frase = frase[:inicio] + complemento_usuario + frase[fim+1:]
        # Se não tem placeholder, anexa ao final (ou substitui opção se tiver barra)
        else:
            frase += f" {complemento_usuario}"
            
    # Limpa placeholders que sobraram (vazios)
    frase = re.sub(r'\{.*?\}', '', frase)
    return re.sub(r'\s+', ' ', frase).strip()

def extrair_texto_anterior(texto_completo):
    if not texto_completo: return {}
    texto = texto_completo.replace("\n", " ").strip()
    secoes = {
        "CONTEXTO": r"(Admissão|PO imediato|PO tardio|Paciente)", 
        "NEURO": r"(NEURO|Neuro)", "RESP": r"(RESP|Resp|AR:)",
        "CARDIO": r"(CARDIO|Cardio|CV:|ACV:)", "TGI": r"(TGI|Tgi)",
        "RENAL": r"(RENAL|Renal|TGU)", "INFECTO": r"(INFECTO|Infecto|Hemato)",
        "GERAL": r"(GERAL|Geral|Ext\.|Miscelânea)"
    }
    indices = []
    for chave, regex in secoes.items():
        match = re.search(regex, texto)
        if match: indices.append((match.start(), chave))
    indices.sort()
    resultado = {}
    for i in range(len(indices)):
        start, chave = indices[i]
        if i < len(indices) - 1:
            end = indices[i+1][0]
            conteudo = texto[start:end]
        else:
            end_conduta = re.search(r"(CONDUTAS|Condutas|///)", texto[start:])
            conteudo = texto[start : start + end_conduta.start()] if end_conduta else texto[start:]
        conteudo = re.sub(r"^(NEURO|Neuro|RESP|Resp|CV:|ACV:|TGI|RENAL|Renal|TGU|INFECTO|Infecto|Hemato|GERAL|Geral)[:.]\s*", "", conteudo).strip()
        resultado[chave] = conteudo
    return resultado

# ==============================================================================
# INTERFACE STREAMLIT
# ==============================================================================

st.title("🏥 Gerador de Evolução UTI")

# --- COLUNA LATERAL (DADOS VITAIS) ---
with st.sidebar:
    st.header("Dados do Paciente")
    leito = st.text_input("Leito", placeholder="Ex: 01")
    tax = st.text_input("TAX (ºC)")
    diurese = st.text_input("Diurese (ml)")
    bh = st.text_input("Balanço Hídrico")
    
    st.info("💡 **Dica:** Copie a evolução de ontem abaixo para puxar os dados.")
    txt_ant = st.text_area("Evolução Anterior", height=200)

# Dados para injeção
dados_vitais = {"tax": tax, "quant": diurese, "bh": bh}
# Parse do texto antigo
texto_antigo_parseado = extrair_texto_anterior(txt_ant)

# --- ABA DE LABORATÓRIOS ---
with st.expander("🧪 LABORATÓRIOS (Comparativo Automático)", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    cols = [col1, col2, col3, col4]
    
    lista_labs = [
        ("Hb", "Hemoglobina"), ("Ht", "Hematócrito"), ("Leucograma", "Leucograma"),
        ("Plaquetas", "Plaquetas"), ("PCR", "PCR"), ("INR", "INR/TAP"),
        ("Ureia", "Ureia"), ("Creatinina", "Creatinina"), ("Sódio", "Sódio"),
        ("Potássio", "Potássio"), ("Magnésio", "Magnésio"), ("Cálcio", "Cálcio"),
        ("Lactato", "Lactato"), ("Troponina", "Troponina"), ("pH", "pH"),
        ("pCO2", "pCO2"), ("pO2", "pO2"), ("Bicarbonato", "Bicarbonato"),
        ("TGO", "TGO"), ("TGP", "TGP"), ("Bilirrubinas", "Bilirrubinas")
    ]
    
    labs_preenchidos = {}
    
    for i, (chave, nome) in enumerate(lista_labs):
        # Busca valor antigo
        ant = buscar_valor_antigo(txt_ant, chave)
        label = f"{nome} (Ant: {ant})" if ant else nome
        
        # Cria input na coluna certa
        with cols[i % 4]:
            novo_val = st.text_input(label, key=f"lab_{chave}")
            
        if novo_val:
            if ant and novo_val != ant:
                labs_preenchidos[chave] = f"{ant}->{novo_val}"
            else:
                labs_preenchidos[chave] = novo_val
                
    outros_labs = st.text_input("Outros Exames (Ex: Amilase 50)")
    if outros_labs: labs_preenchidos["Outros"] = outros_labs

# --- SISTEMAS CLÍNICOS ---
sistemas = ["CONTEXTO", "NEURO", "RESP", "CARDIO", "TGI", "RENAL", "INFECTO", "GERAL"]
blocos_finais = {}
condutas_detectadas = []
rastreador_uso = set()

st.markdown("---")

for sis in sistemas:
    # Recupera texto anterior se houver
    prev_text = texto_antigo_parseado.get(sis, "")
    
    with st.expander(f"**{sis}**" + (f" (Anterior: {prev_text[:30]}...)" if prev_text else ""), expanded=False):
        
        # Opções do Banco de Dados
        opcoes = ["Selecione..."] + DB_FRASES[sis]
        escolha = st.selectbox(f"Frase Principal ({sis})", options=opcoes, key=f"sel_{sis}")
        
        # Se tiver barra na escolha, oferece Radio Button para refinar
        frase_processada = escolha
        if "/" in escolha and escolha != "Selecione..." and not any(tp in escolha for tp in TERMOS_PROTEGIDOS):
            subs = [op.strip() for op in escolha.split("/")]
            sub_escolha = st.radio("Refinar opção:", subs, key=f"rad_{sis}", horizontal=True)
            frase_processada = sub_escolha
            
        # Campo para Complemento ou Texto Livre
        complemento = st.text_input(f"Complemento / Texto Livre ({sis})", key=f"comp_{sis}", placeholder="Digite detalhes ou texto livre aqui...")
        
        # LÓGICA DE MONTAGEM DO PARÁGRAFO
        texto_final_sis = ""
        
        # 1. Se usuário não escolheu frase nem escreveu nada, MANTEM ANTERIOR
        if escolha == "Selecione..." and not complemento:
            texto_final_sis = prev_text
            
        # 2. Se escolheu frase
        elif escolha != "Selecione...":
            texto_final_sis = processar_frase_ui(frase_processada, complemento, dados_vitais)
            # Rastreia vitais usados
            for k, v in dados_vitais.items():
                if v and v in texto_final_sis: rastreador_uso.add(k)
        
        # 3. Se só escreveu texto livre (escolha vazia)
        elif escolha == "Selecione..." and complemento:
            # Se tiver texto anterior, anexa. Se não, é só o novo.
            if prev_text:
                texto_final_sis = f"{complemento}. {prev_text}"
            else:
                texto_final_sis = complemento

        # --- LÓGICA DE EXAMES E VITAIS AUTOMÁTICOS ---
        
        # Auto-Append Vitais (se não foram usados no texto)
        extras = []
        if sis == "INFECTO" and "tax" not in rastreador_uso and tax:
            extras.append(f"TAX: {tax}ºC")
        if sis == "RENAL":
            if "quant" not in rastreador_uso and diurese: extras.append(f"Diurese: {diurese}ml")
            if "bh" not in rastreador_uso and bh: extras.append(f"BH: {bh}")
            
        if extras:
            add = ". ".join(extras)
            texto_final_sis = f"{texto_final_sis}. {add}" if texto_final_sis else add

        # Append Labs
        l_txt = []
        mapa_abrev = MAPA_EXAMES_SISTEMA.get(sis, {})
        for nome_interno, abreviacao in mapa_abrev.items():
            if nome_interno in labs_preenchidos:
                l_txt.append(f"{abreviacao}: {labs_preenchidos[nome_interno]}")
        if sis == "INFECTO" and "Outros" in labs_preenchidos:
            l_txt.append(labs_preenchidos["Outros"])
            
        if l_txt:
            l_str = " [Labs: " + " | ".join(l_txt) + "]"
            # Evita duplicar labs se já vieram do texto copiado
            if l_str not in texto_final_sis:
                texto_final_sis = (texto_final_sis + "." + l_str) if texto_final_sis else ("Dados: " + l_str)

        # Salva o bloco e busca condutas
        blocos_finais[sis] = texto_final_sis
        for g in GATILHOS_CONDUTA:
            if g in texto_final_sis.lower():
                condutas_detectadas.append(texto_final_sis) # Adiciona a frase toda ou parte dela
                break

# ==============================================================================
# GERAÇÃO FINAL
# ==============================================================================

st.markdown("---")
st.header("📝 Texto Final")

hoje = datetime.date.today().strftime('%d/%m/%Y')
texto_completo = f"=== EVOLUÇÃO - LEITO {leito} ({hoje}) ===\n\n"

if blocos_finais["CONTEXTO"]: 
    texto_completo += f"{blocos_finais['CONTEXTO']}.\n\n"

for sis in sistemas[1:]: # Pula Contexto
    conteudo = blocos_finais[sis]
    if conteudo and conteudo != "Dados: [Labs: ]":
        # Limpeza fina
        conteudo = conteudo.replace("..", ".").replace(". [", ". [").strip()
        texto_completo += f"{sis}: {conteudo}.\n"

texto_completo += "\n/// CONDUTAS ///\n"
if condutas_detectadas:
    # Filtra frases repetidas e formata
    condutas_unicas = list(set(condutas_detectadas))
    for c in condutas_unicas:
        # Tenta pegar só o trecho relevante se possível, ou a frase toda
        texto_completo += f"- {c.strip()}.\n"
else:
    texto_completo += "- Mantidas.\n"

st.text_area("Copie aqui:", value=texto_completo, height=400)
