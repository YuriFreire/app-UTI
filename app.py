import streamlit as st
import re
import datetime

# ==============================================================================
# CONFIGURAÇÕES DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Gerador de Evolução UTI", page_icon="🏥", layout="wide")

st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 3rem;}
        h1 {font-size: 1.5rem; margin-bottom: 0.5rem;}
        .stRadio label {font-weight: bold; color: #31333F;}
        .stTextInput label {font-size: 14px;}
        hr {margin-top: 0.5rem; margin-bottom: 0.5rem;}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. BANCO DE DADOS E GATILHOS
# ==============================================================================

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
        "Neurocrítico (HIC/AVE/TCE), medidas de neuroproteção mantidas",
        "Reabordado cirurgicamente em {data} para {procedimento}",
        "Internação prolongada por complicações de {causa}",
        "Paciente em cuidados paliativos / Limitação de esforço terapêutico"
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
        "Associado anti-hipertensivo oral ({droga})",
        "Ritmo Sinusal / Fibrilação Atrial (FA)",
        "FA controlada com {droga} (FC {fc}bpm)",
        "Bem perfundido (TEC < 3s, Lac normal) / Má perfusão (TEC > 4s)",
        "Hipertenso, em uso de Nitroprussiato {vazao} ml/h",
        "Hipotenso, realizada expansão volêmica com {quant} ml",
        "Extremidades quentes / Extremidades frias",
        "Suspenso antiagregante / Suspenso anticoagulação",
        "Solicitado Ecocardiograma (ECOTT)"
    ],
    "RESP": [
        "Eupneico em ar ambiente (AA), confortável",
        "Em uso de Cateter Nasal (CN) {litros} L/min",
        "Em Máscara de Venturi {perc}%",
        "VM via TOT, modo {modo} / VM via TQT",
        "Parâmetros: Vol {vol}ml, PEEP {peep}, FIO2 {fio}%",
        "Desconforto respiratório leve / moderado / intenso",
        "Em VNI intermitente ({motivo})",
        "Extubação realizada no período sem intercorrências",
        "Ausculta: Murmúrio vesicular presente / Creptos em {loc} / Roncos",
        "Secretividade aumentada, aspecto {aspecto}",
        "Dreno de tórax à {lado} oscilante / borbulhante / improdutivo",
        "Hiperemia e secreção em estoma de traqueostomia",
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
        "Ruídos hidroaéreos presentes / RHA diminuídos ou ausentes",
        "Evacuações presentes ({aspecto}) / Ausentes",
        "Dejeções ausentes há {dias} dias (Iniciado laxativos)",
        "Glicemias controladas / Labéis (Iniciado Insulina)",
        "Em uso de procinéticos e inibidor de bomba de prótons (IBP)",
        "Saída de secreção peri-sonda (GTT/SNE)"
    ],
    "RENAL": [
        "Diurese espontânea conservada e clara",
        "Diurese via Sonda Vesical (SVD), aspecto {aspecto}",
        "Irrigação vesical contínua (hematúria {tipo}) / Sem irrigação",
        "Oligúria, realizado estímulo diurético com {droga}",
        "Poliúria (> 3ml/kg/h), vigiando eletrólitos",
        "Função renal preservada / Função renal alterada (estável)",
        "Função renal em melhora / Função renal em piora",
        "Em Hemodiálise (HD) intermitente / Em CVVHD",
        "Sem distúrbios hidroeletrolíticos graves / Reposição de K/Mg",
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
        "Leucocitose mantida / Leucograma em melhora",
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
# 2. FUNÇÕES DE SUPORTE
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
# 3. INTERFACE STREAMLIT (Lógica Dinâmica)
# ==============================================================================

st.title("🏥 Gerador de Evolução UTI")

# --- SIDEBAR: DADOS VITAIS ---
with st.sidebar:
    st.header("Paciente")
    leito = st.text_input("Leito", placeholder="Ex: 01")
    tax = st.text_input("TAX (ºC)")
    diurese = st.text_input("Diurese (ml)")
    bh = st.text_input("Balanço Hídrico")
    st.info("Cole a evolução anterior para puxar dados:")
    txt_ant = st.text_area("Evolução Anterior", height=150)

# Dicionário de vitais para substituição rápida
dados_vitais = {"tax": tax, "quant": diurese, "bh": bh}
texto_antigo_parseado = extrair_texto_anterior(txt_ant)

# --- ABA DE LABORATÓRIOS ---
with st.expander("🧪 LABORATÓRIOS (Preencher)", expanded=True):
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
        ant = buscar_valor_antigo(txt_ant, chave)
        label = f"{nome} (Ant: {ant})" if ant else nome
        with cols[i % 4]:
            val = st.text_input(label, key=f"lab_{chave}")
            if val:
                if ant and val != ant: labs_preenchidos[chave] = f"{ant}->{val}"
                else: labs_preenchidos[chave] = val
    
    outros = st.text_input("Outros Exames")
    if outros: labs_preenchidos["Outros"] = outros

# --- SISTEMAS CLÍNICOS (GERAÇÃO DINÂMICA) ---
sistemas = ["CONTEXTO", "NEURO", "RESP", "CARDIO", "TGI", "RENAL", "INFECTO", "GERAL"]
blocos_finais = {}
condutas_detectadas = []
rastreador_uso = set()

st.markdown("---")

for sis in sistemas:
    prev_text = texto_antigo_parseado.get(sis, "")
    
    with st.expander(f"**{sis}**" + (f" (Anterior: {prev_text[:40]}...)" if prev_text else ""), expanded=False):
        
        # 1. Múltipla Escolha
        escolhas = st.multiselect(
            f"Selecione as frases para {sis}:", 
            options=DB_FRASES[sis],
            key=f"multi_{sis}"
        )
        
        frases_selecionadas = []
        
        # 2. Loop Dinâmico: Para cada escolha, mostra refinamentos específicos
        for i, item in enumerate(escolhas):
            texto_base = item
            
            # (A) Se tiver barra (/), mostra Radio Button
            # Verifica se é uma barra de opção real, não de unidade
            tem_barra = "/" in item and not any(tp in item for tp in TERMOS_PROTEGIDOS)
            
            if tem_barra:
                opcoes_radio = [x.strip() for x in item.split("/")]
                # O label é um pedaço da frase pra identificar
                sub_escolha = st.radio(
                    f"👉 Opção para: *'{item[:40]}...'*", 
                    opcoes_radio, 
                    key=f"rad_{sis}_{item}", # Key única baseada na frase
                    horizontal=True
                )
                texto_base = sub_escolha
            
            # (B) Se tiver Variável ({dose}, {droga}), mostra Text Input
            # Isso acontece DEPOIS de resolver o radio (caso a opção escolhida tenha variável)
            if "{" in texto_base:
                # Encontra o que está dentro das chaves para usar no label
                match = re.search(r"\{(.*?)\}", texto_base)
                label_ph = match.group(1) if match else "valor"
                
                # Se for um vital global (tax, bh), já tenta preencher, senão pede input
                if label_ph in dados_vitais and dados_vitais[label_ph]:
                    texto_base = texto_base.replace(f"{{{label_ph}}}", dados_vitais[label_ph])
                    rastreador_uso.add(label_ph)
                else:
                    val_input = st.text_input(
                        f"✏️ Preencha **{label_ph}** para: *'{texto_base}'*", 
                        key=f"in_{sis}_{item}_{label_ph}"
                    )
                    if val_input:
                        texto_base = texto_base.replace(f"{{{label_ph}}}", val_input)
                    else:
                        # Limpa se não preencher
                        texto_base = re.sub(r'\{.*?\}', '', texto_base)
            
            # Adiciona a frase processada na lista
            frases_selecionadas.append(texto_base)
            
        # 3. Campo Livre (Complemento)
        complemento = st.text_input(f"Texto Livre / Complemento ({sis})", key=f"comp_{sis}")
        
        # 4. Montagem Final do Bloco
        partes = frases_selecionadas[:]
        if complemento:
            partes.append(complemento)
            
        # Lógica: Se não marcou nada, mantém anterior. Se marcou, substitui.
        if not partes and prev_text:
            texto_final_sis = prev_text
        else:
            texto_final_sis = ". ".join(partes)
            
        # --- Auto-Append Vitais ---
        extras = []
        if sis == "INFECTO" and "tax" not in rastreador_uso and tax:
            extras.append(f"TAX: {tax}ºC")
        if sis == "RENAL":
            if "quant" not in rastreador_uso and diurese: extras.append(f"Diurese: {diurese}ml")
            if "bh" not in rastreador_uso and bh: extras.append(f"BH: {bh}")
            
        if extras:
            add = ". ".join(extras)
            texto_final_sis = f"{texto_final_sis}. {add}" if texto_final_sis else add

        # --- Auto-Append Labs ---
        l_txt = []
        mapa_abrev = MAPA_EXAMES_SISTEMA.get(sis, {})
        for nome_interno, abreviacao in mapa_abrev.items():
            if nome_interno in labs_preenchidos:
                l_txt.append(f"{abreviacao}: {labs_preenchidos[nome_interno]}")
        if sis == "INFECTO" and "Outros" in labs_preenchidos:
            l_txt.append(labs_preenchidos["Outros"])
            
        if l_txt:
            l_str = " [Labs: " + " | ".join(l_txt) + "]"
            if l_str not in texto_final_sis:
                texto_final_sis = (texto_final_sis + "." + l_str) if texto_final_sis else ("Dados: " + l_str)

        blocos_finais[sis] = texto_final_sis.replace("..", ".").strip()
        
        # Caça condutas
        for g in GATILHOS_CONDUTA:
            if g in texto_final_sis.lower():
                condutas_detectadas.append(texto_final_sis)
                break

# ==============================================================================
# GERAÇÃO FINAL
# ==============================================================================
st.markdown("---")
st.header("📝 Resultado Final")

hoje = datetime.date.today().strftime('%d/%m/%Y')
texto_completo = f"=== EVOLUÇÃO - LEITO {leito} ({hoje}) ===\n\n"

if blocos_finais["CONTEXTO"]: 
    texto_completo += f"{blocos_finais['CONTEXTO']}.\n\n"

for sis in sistemas[1:]: 
    conteudo = blocos_finais[sis]
    if conteudo and conteudo != "Dados: [Labs: ]":
        texto_completo += f"{sis}: {conteudo}.\n"

texto_completo += "\n/// CONDUTAS ///\n"
if condutas_detectadas:
    condutas_unicas = list(set(condutas_detectadas))
    for c in condutas_unicas:
        texto_completo += f"- {c.strip()}.\n"
else:
    texto_completo += "- Mantidas.\n"

st.text_area("Copie aqui:", value=texto_completo, height=400)
