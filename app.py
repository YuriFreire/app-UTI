import streamlit as st
import re
import datetime
import hashlib

# ==============================================================================
# 1. CONFIGURAÇÕES VISUAIS & SETUP
# ==============================================================================
st.set_page_config(page_title="Gerador de Evolução UTI Pro", page_icon="🏥", layout="wide")

st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 3rem;}
        h1 {font-size: 1.5rem; margin-bottom: 0.5rem;}
        .stRadio label {font-weight: bold; color: #31333F;}
        .stTextInput label {font-size: 14px;}
        hr {margin-top: 0.5rem; margin-bottom: 0.5rem;}
        /* Ajuste visual para separar melhor os blocos */
        .streamlit-expanderHeader {font-weight: bold; font-size: 1.1em;}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LISTAS E BANCO DE DADOS
# ==============================================================================

TERMOS_PROTEGIDOS = [
    "s/n", "S/N", "mg/dL", "g/dL", "U/L", "U/ml", "mcg/kg/min", "ml/h", 
    "ml/kg", "ml/kg/h", "L/min", "c/d", "s/d", "A/C", "P/F", "b/min", "bpm", 
    "24/24h", "12/12h", "AA", "PO", "SVD", "CN", "TOT", "TQT", "UI/h"
]

GATILHOS_CONDUTA = [
    "realizo", "realizado", "fiz", "feito", "solicito", "solicitado", "peço", 
    "inicio", "iniciado", "começo", "mantenho", "mantido", "suspendo", "suspenso", 
    "retiro", "retirado", "ajusto", "ajustado", "corrijo", "corrigido", "troco", 
    "trocado", "desligo", "desligado", "aumento", "aumentado", "reduzo", "reduzido", 
    "prescrevo", "prescrito", "instalo", "instalado", "passo", "passado", 
    "otimizo", "otimizado", "escalono", "escalonado", "descalono", "adiciono", "associo",
    "transiciono", "deambulou", "sedestrou", "desmamado", "exteriorizou", "reabordado", "feita"
]

MAPA_EXAMES_SISTEMA = {
    "RENAL":  {"Ureia": "Ur", "Creatinina": "Cr", "Sódio": "Na", "Potássio": "K", "Magnésio": "Mg", "Fósforo": "P", "Cálcio": "Ca", "Bicarbonato": "Bic"},
    "INFECTO": {"Leucograma": "Leucograma", "Hb": "Hb", "Ht": "Ht", "Plaquetas": "Plq", "PCR": "PCR", "Procalcitonina": "PCT", "INR": "INR"},
    "CARDIO": {"Lactato": "Lac", "Troponina": "Tropo", "CK-MB": "CKMB", "BNP": "BNP", "D-dímero": "D-dim", "SvO2": "SvO2", "GapCO2": "GapCO2"},
    "TGI":    {"TGO": "TGO", "TGP": "TGP", "GGT": "GGT", "FA": "FA", "Bilirrubinas": "BT", "Amilase": "Amil", "Lipase": "Lip"},
    "RESP":   {"pH": "pH", "pCO2": "pCO2", "pO2": "pO2", "SatO2": "Sat", "Rel. P/F": "P/F", "BE": "BE"},
    "GERAL":  {} # Inicializado vazio para evitar KeyErrors, mas processado logicamente
}

SINONIMOS_BUSCA = {
    "Hb": ["hb", "hgb"], "Ht": ["ht", "hto"], "Leucograma": ["leuco", "leucocitos", "leucograma"],
    "Plaquetas": ["plq", "plaquetas"], "PCR": ["pcr"], "INR": ["inr"],
    "Ureia": ["ureia", "ur"], "Creatinina": ["cr", "creat"],
    "Sódio": ["sodio", "na"], "Potássio": ["potassio", "k"], "Magnésio": ["magnesio", "mg"],
    "Cálcio": ["calcio", "ca"], "Lactato": ["lactato", "lac"],
    "pH": ["ph"], "pCO2": ["pco2"], "pO2": ["po2"], "Bicarbonato": ["bic", "hco3"],
    "TGO": ["tgo", "ast"], "TGP": ["tgp", "alt"], "Bilirrubinas": ["bt", "bilirrubina total"]
}

DB_FRASES = {
    "CONTEXTO": [
        "PO de {procedimento}, sem intercorrências",
        "Paciente {idade}, portador de {comorbidades}",
        "PO tardio de {procedimento} ({data}), evoluindo estável",
        "Admissão na UTI pós {procedimento} / com quadro de {quadro} / trazido para UTI por {motivo}",
        "Paciente em tratamento de Choque Séptico (Foco: {foco})",
        "Reabordado cirurgicamente em {data} para {procedimento}",
        "Internação prolongada por complicações de {causa}",
        "Paciente em cuidados paliativos / Limitação de esforço terapêutico"
    ],
    "NEURO": [
        "RASS 0, vigil, colaborativo, orientado",
        "RASS -1 a -3",
        "RASS -4/-5, comatoso / Agitado (RASS +)",
        "Sem sedação / Desligada sedação / Sedação suspensa / Reduzido sedação",
        "Sedado com {drogas} (RASS {rass})",
        "Analgesia otimizada com {droga} / Necessitou ansiólise ({droga})",
        "Pupilas isocóricas / Anisocoria / Pupilas {tamanho}",
        "Sem déficits focais / Hemiparesia à {lado}",
        "Força muscular preservada / Diminuída em {loc} (Grau {grau})",
        "Reflexos de tronco preservados / Abolidos",
        "Sem crises convulsivas / Crises no período (cd: {conduta})",
        "Deambulou no período / Sedestrou / Restrito ao leito",
        "Sialorréico (medidas xerostômicas)",
        "Com bom controle de tronco / Sem controle de tronco",
        "CAM-ICU+ / CAM-ICU negativo",
        "CPOT negativo / CPOT positivo | BPS negativo / BPS positivo",
        "Disártrico / Afásico / Contactuante",
        "NIHSS {pts} pts ({detalhe})",
        "Sem sinais de encefalopatia / Com sinais de encefalopatia"
    ],
    "CARDIO": [
        "Hemodinâmica estável, sem drogas vasoativas (DVA)",
        "Instabilidade hemodinâmica / Choque",
        "Em uso de Noradrenalina {dose} mcg/kg/min / Em uso de Noradrenalina {dose} e Vasopressina {vazao} UI/h",
        "Iniciado Dobutamina {dose} mcg/kg/min",
        "Em desmame de DVA (Noradrenalina {dose})",
        "Desligo DVA / DVA desligada",
        "Iniciado RCP",
        "POCUS evidenciando {achado}",
        "Desmamado vasodilatador, iniciado oral ({droga})",
        "Associado anti-hipertensivo oral ({droga})",
        "Ritmo Sinusal / Fibrilação Atrial (FA)",
        "FA controlada com {droga} (FC {fc}bpm)",
        "Bem perfundido (TEC < 3s, Lac normal)",
        "Com sinais de má perfusão (frio, TEC > 4s, livedo)",
        "Hipertenso, em uso de Nitroprussiato {vazao} ml/h",
        "Hipotenso, realizada expansão volêmica com {quant} ml",
        "Extremidades quentes / Extremidades frias",
        "Suspenso antiagregante / Suspenso anticoagulação",
        "Solicitado Ecocardiograma (ECOTT)"
    ],
    "RESP": [
        "Eupneico em ar ambiente (AA), confortável, com boa SO2",
        "Padrão A pulmonar / Padrão B / Padrão C",
        "PCO2 elevada",
        "Em uso de Cateter Nasal (CN) {litros} L/min",
        "Boas trocas / Trocas ruins (P/F {pf})",
        "Melhora da hipoxemia / Tolerando SO2 mais baixas",
        "Com atividade expiratória / Sem atividade expiratória",
        "Apresentando taquidispneia",
        "Em Máscara de Venturi {perc}%",
        "VM via TOT, modo {modo} / VM via TQT",
        "TQT plástica / TQT metálica",
        "Parâmetros: Vol {vol}ml, PEEP {peep}, FIO2 {fio}%",
        "Desconforto respiratório leve / moderado / intenso",
        "Em VNI intermitente ({motivo})",
        "Extubação realizada no período sem intercorrências",
        "Ausculta: Murmúrio vesicular presente / Creptos em {loc} / Roncos",
        "Secretividade aumentada, aspecto {aspecto}",
        "Dreno de tórax à {lado} oscilante / borbulhante / improdutivo / produtivo",
        "TC de Tórax: {laudo}"
    ],
    "TGI": [
        "Dieta oral liberada / Aceitação parcial",
        "Dieta oral zero / Dieta oral liberada pela fonoaudiologia",
        "SNG produtiva / SNG improdutiva",
        "Dieta enteral via SNE/GTT a {vazao}ml/h",
        "Iniciado dieta enteral / Progressão de dieta",
        "Suspenso NPT, iniciado dieta enteral",
        "Dieta zero / Dieta suspensa por {motivo}",
        "Nutrição Parenteral Total (NPT) em curso",
        "Retirado SNG no período",
        "Abdome flácido, indolor / Globoso e distendido",
        "Ruídos hidroaéreos presentes / RHA diminuídos ou ausentes",
        "Dejeções presentes ({aspecto}) / Dejeções Ausentes",
        "Dejeções ausentes há {dias} dias (Iniciado laxativos)",
        "Glicemias controladas / Glicemias com escapes (ajustado/iniciado insulina)",
        "Em uso de procinéticos / IBP profilático / IBP pleno"
    ],
    "RENAL": [
        "Diurese espontânea conservada e clara",
        "Em TSR / iniciou HD / não tolerou HD",
        "Diurese via Sonda Vesical (SVD), aspecto {aspecto}",
        "Irrigação vesical contínua / Sem irrigação",
        "Oligúrico / realizado estímulo diurético / reduzido diurético",
        "Poliúria (> 3ml/kg/h) / anúrico",
        "Função renal preservada / Função renal alterada (em melhora / em piora)",
        "Função renal em melhora / Função renal em piora",
        "Em Hemodiálise (HD) intermitente / Em CVVHD",
        "Sem distúrbios hidroeletrolíticos graves / Reposição de K/Mg/Ca/Na/água",
        "Nefrostomia produtiva ({quant}ml) / improdutiva",
        "Balanço Hídrico negativo / BH positivo / BH neutro"
    ],
    "INFECTO": [
        "Afebril nas últimas 24h, curva térmica estável",
        "Subfebril no período / Picos febris isolados ({valor}ºC)",
        "Em uso de antibiótico: {atb} / Sem antibióticos",
        "Escalonado antibiótico para {novo} / Suspenso antibiótico",
        "Sem foco infeccioso aparente",
        "Curativos limpos e secos / Deiscência de ferida / Piora infecciosa",
        "Sem sinais de infecção em óstio / Com sinais de infecção de óstio",
        "Leucocitose mantida / Leucograma em melhora / Leucograma elevado",
        "Hb estável / Hb em queda",
        "Atb ajustado para função renal / Atb dose full",
        "Sem exteriorizar sangramentos / Sangramento ativo em {sítio}",
        "Feito CH / Iniciado anticoagulação plena"
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
# 3. FUNÇÕES DE SUPORTE E LÓGICA
# ==============================================================================

def criar_hash_estavel(texto):
    """Cria um hash único e estável para usar como chave de widget."""
    return hashlib.md5(texto.encode('utf-8')).hexdigest()

def extrair_condutas_inteligente(texto_completo, gatilhos):
    if not texto_completo: return []
    verbos_regex = r"|".join([re.escape(v) for v in gatilhos])
    # Separa por pontos e ponto-e-vírgula, ignora quebras de linha dentro da frase
    fatias = re.split(r'[.;]\s+', texto_completo.replace("\n", " "))
    condutas_finais = []
    for fatia in fatias:
        fatia = fatia.strip()
        if not fatia: continue
        # Verifica se começa com um verbo de ação
        match = re.search(rf"^({verbos_regex})\b", fatia, re.IGNORECASE)
        if match:
            # Filtra falsos positivos como "Não realizo"
            if re.search(r"\bn[ãa]o\s+" + re.escape(match.group(1)), fatia, re.IGNORECASE):
                continue
            condutas_finais.append(fatia)
    return sorted(list(set(condutas_finais)))

def buscar_valor_antigo(texto, chave):
    if not texto: return None
    termos = SINONIMOS_BUSCA.get(chave, [chave.lower()])
    for t in termos:
        pattern = rf"\b{re.escape(t)}[:=\s]*([0-9][0-9.,\s>\-]*(?:R|reposto)?)"
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            cadeia = match.group(1).strip()
            # Verifica se tem 'R' ou 'reposto'
            match_reposto = re.search(r'([0-9.,]+)\s*[-–]?\s*(R|reposto)$', cadeia, re.IGNORECASE)
            if match_reposto:
                val = match_reposto.group(1)
                indicador = match_reposto.group(2)
                return f"{val} - {indicador}"
            else:
                # Limpa sujeira
                cadeia_limpa = re.sub(r'[>\-]', ' ', cadeia)
                numeros = [n for n in cadeia_limpa.split() if n[0].isdigit()]
                if numeros: return numeros[-1]
    return None

def extrair_texto_anterior(texto_completo):
    if not texto_completo: return {}
    texto = texto_completo.replace("\n", " ").strip()
    
    # Regex melhorado para capturar variações
    secoes = {
        "CONTEXTO": r"(Admissão|PO imediato|PO tardio|Paciente)", 
        "NEURO": r"(NEURO|Neuro|Neurologia)", 
        "RESP": r"(RESP|Resp|Respiratória|AR:)",
        "CARDIO": r"(CARDIO|Cardio|Cardiovascular|CV:|ACV:)", 
        "TGI": r"(TGI|Tgi|Gastro|Abdome)",
        "RENAL": r"(RENAL|Renal|TGU|Urológico)", 
        "INFECTO": r"(INFECTO|Infecto|Infecciosa|Hemato)",
        "GERAL": r"(GERAL|Geral|Ext\.|Miscelânea|Outros)"
    }
    
    indices = []
    for chave, regex in secoes.items():
        match = re.search(regex, texto)
        if match: indices.append((match.start(), chave))
    
    indices.sort()
    resultado = {}
    
    for i in range(len(indices)):
        start, chave = indices[i]
        
        # Define o fim da seção atual
        if i < len(indices) - 1:
            end = indices[i+1][0]
            conteudo = texto[start:end]
        else:
            # Se for a última seção encontrada, vai até o marcador de CONDUTAS ou Fim
            end_conduta = re.search(r"(CONDUTAS|Condutas|///|Planos)", texto[start:])
            if end_conduta:
                conteudo = texto[start : start + end_conduta.start()]
            else:
                conteudo = texto[start:]
        
        # Limpa o cabeçalho (ex: "NEURO:") do conteúdo capturado
        pattern_clean = r"^(NEURO|Neuro|RESP|Resp|CV:|ACV:|TGI|RENAL|Renal|TGU|INFECTO|Infecto|Hemato|GERAL|Geral|Ext\.|Miscelânea|Outros|Respiratória|Neurologia|Cardiovascular|Gastro|Urológico|Infecciosa)[:.]\s*"
        conteudo = re.sub(pattern_clean, "", conteudo).strip()
        resultado[chave] = conteudo
        
    return resultado

def limpar_dados_antigos(texto, dados_novos, limpar_labs=False):
    if not texto: return ""
    novo_texto = texto
    
    if dados_novos.get('tax'):
        novo_texto = re.sub(r"TAX:\s*[\d.,]+\s*ºC?", "", novo_texto, flags=re.IGNORECASE)
    if dados_novos.get('quant'):
        novo_texto = re.sub(r"Diurese:\s*[\d.,]+\s*(ml)?", "", novo_texto, flags=re.IGNORECASE)
    if dados_novos.get('bh'):
        novo_texto = re.sub(r"BH:\s*[+-]?\s*[\d.,]+", "", novo_texto, flags=re.IGNORECASE)
        
    if limpar_labs:
        novo_texto = re.sub(r"\[Labs:.*?\]", "", novo_texto, flags=re.IGNORECASE)
        novo_texto = re.sub(r"Dados:\s*$", "", novo_texto.strip())
        
    # Limpeza de pontuação duplicada
    novo_texto = re.sub(r"\.\s*\.", ".", novo_texto)
    novo_texto = re.sub(r"\s+", " ", novo_texto)
    return novo_texto.strip()

# ==============================================================================
# 4. INTERFACE STREAMLIT
# ==============================================================================

st.title("🏥 Gerador de Evolução UTI - V35.1")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Paciente")
    leito = st.text_input("Leito", placeholder="Ex: 01")
    tax = st.text_input("TAX (ºC)")
    diurese = st.text_input("Diurese (ml)")
    bh = st.text_input("Balanço Hídrico")
    st.markdown("---")
    st.info("Copie a evolução anterior:")
    txt_ant = st.text_area("Anterior", height=200, help="Cole aqui a evolução do dia anterior para extração de dados.")

dados_vitais = {"tax": tax, "quant": diurese, "bh": bh}
texto_antigo_parseado = extrair_texto_anterior(txt_ant)

# --- LABS ---
with st.expander("🧪 LABORATÓRIOS (Comparativo)", expanded=True):
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
    
    outros = st.text_input("Outros Exames (Texto livre)")
    if outros: labs_preenchidos["Outros"] = outros

# --- SISTEMAS ---
sistemas = ["CONTEXTO", "NEURO", "RESP", "CARDIO", "TGI", "RENAL", "INFECTO", "GERAL"]
blocos_finais = {}
rastreador_uso = set()

st.markdown("---")

for sis in sistemas:
    prev_text_raw = texto_antigo_parseado.get(sis, "")
    tem_novos_labs_sis = False
    mapa_abrev = MAPA_EXAMES_SISTEMA.get(sis, {})
    
    # Verifica se há novos labs para este sistema
    for k in mapa_abrev:
        if k in labs_preenchidos: tem_novos_labs_sis = True
    if sis == "INFECTO" and "Outros" in labs_preenchidos: tem_novos_labs_sis = True
    
    prev_text_limpo_dados = limpar_dados_antigos(prev_text_raw, dados_vitais, limpar_labs=tem_novos_labs_sis)
    
    # Título do Expander com preview
    preview = f" (Anterior: {prev_text_limpo_dados[:40]}...)" if prev_text_limpo_dados else ""
    with st.expander(f"**{sis}**{preview}", expanded=False):
        
        escolhas = st.multiselect(
            f"Selecione as frases para {sis}:", 
            options=DB_FRASES.get(sis, []),
            key=f"multi_{sis}"
        )
        
        frases_do_sistema = []
        
        # --- LÓGICA CORRIGIDA: Usa Hash do item para garantir que os widgets não sumam ---
        for item in escolhas:
            texto_base = item
            tem_barra = "/" in item and not any(tp in item for tp in TERMOS_PROTEGIDOS)
            
            # Gera chave única baseada no TEXTO, não no índice
            item_hash = criar_hash_estavel(item)
            
            if tem_barra:
                opcoes_radio = [x.strip() for x in item.split("/")]
                # Chave robusta
                sub_escolha = st.radio(
                    f"Refinar: {item[:40]}...", 
                    opcoes_radio, 
                    key=f"radio_{sis}_{item_hash}",
                    horizontal=True
                )
                texto_base = sub_escolha
            
            # Preenchimento de variáveis {placeholder}
            if "{" in texto_base:
                match = re.search(r"\{(.*?)\}", texto_base)
                label_ph = match.group(1) if match else "valor"
                
                # Se o dado já existe nos vitais (ex: tax, bh), usa direto
                if label_ph in dados_vitais and dados_vitais[label_ph]:
                    texto_base = texto_base.replace(f"{{{label_ph}}}", dados_vitais[label_ph])
                    rastreador_uso.add(label_ph)
                else:
                    # Input manual para variável
                    val_input = st.text_input(
                        f"✏️ Preencha **{label_ph}** para: *'{texto_base}'*", 
                        key=f"in_{sis}_{item_hash}_{label_ph}"
                    )
                    if val_input: texto_base = texto_base.replace(f"{{{label_ph}}}", val_input)
                    else: texto_base = re.sub(r'\{.*?\}', '', texto_base) # Limpa se vazio
            
            frases_do_sistema.append(texto_base)
            
        complemento = st.text_input(f"Complemento / Texto Livre ({sis})", key=f"comp_{sis}")
        
        # --- MONTAGEM DO TEXTO DO SISTEMA ---
        partes = frases_do_sistema[:]
        if complemento: partes.append(complemento)
            
        if frases_do_sistema:
            # Opção A: Usuário selecionou frases -> Substitui o anterior completamente
            texto_final_sis = ". ".join(partes)
        elif complemento:
            # Opção B: Só escreveu complemento -> Adiciona ao anterior (se existir)
            if prev_text_limpo_dados:
                texto_final_sis = f"{prev_text_limpo_dados} {complemento}"
            else:
                texto_final_sis = complemento
        else:
            # Opção C: Nada feito -> Mantém o anterior
            texto_final_sis = prev_text_limpo_dados
            
        # Append Vitais automáticos (apenas se não usados no texto)
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
        for nome_interno, abreviacao in mapa_abrev.items():
            if nome_interno in labs_preenchidos:
                l_txt.append(f"{abreviacao}: {labs_preenchidos[nome_interno]}")
        
        # Inserção de "Outros" exames especificamente no Infecto
        if sis == "INFECTO" and "Outros" in labs_preenchidos:
            l_txt.append(labs_preenchidos["Outros"])
            
        if l_txt:
            l_str = " [Labs: " + " | ".join(l_txt) + "]"
            # Evita duplicar labs se já estiverem no texto
            if l_str not in texto_final_sis:
                texto_final_sis = (texto_final_sis + "." + l_str) if texto_final_sis else ("Dados: " + l_str)

        blocos_finais[sis] = texto_final_sis.replace("..", ".").strip()

# ==============================================================================
# GERAÇÃO FINAL (COM CONDUTAS)
# ==============================================================================
st.markdown("---")
st.header("📝 Resultado Final")

hoje = datetime.date.today().strftime('%d/%m/%Y')
texto_completo = f"=== EVOLUÇÃO - LEITO {leito} ({hoje}) ===\n\n"

# Contexto sempre primeiro
if blocos_finais.get("CONTEXTO"): 
    texto_completo += f"{blocos_finais['CONTEXTO']}.\n\n"

# Loop pelos sistemas restantes
for sis in sistemas[1:]: 
    conteudo = blocos_finais.get(sis, "")
    
    # Validação robusta: Mostra se tiver conteúdo OU se for INFECTO/GERAL com dados prévios
    # O bug anterior removia INFECTO se só tivesse labs. Corrigido.
    eh_dado_lab_puro = conteudo.startswith("Dados: [Labs:")
    tem_conteudo_real = len(conteudo) > 3
    
    if tem_conteudo_real:
        texto_completo += f"{sis}: {conteudo}.\n"

# Extração de condutas
all_text = " ".join([v for k,v in blocos_finais.items()])
condutas_finais = extrair_condutas_inteligente(all_text, GATILHOS_CONDUTA)

texto_completo += "\n/// CONDUTAS ///\n"
if condutas_finais:
    for c in condutas_finais:
        texto_completo += f"- {c.strip()}.\n"
else:
    texto_completo += "- Mantidas.\n"

st.text_area("Copie aqui:", value=texto_completo, height=500)
