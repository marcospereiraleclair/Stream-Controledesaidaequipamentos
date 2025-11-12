import streamlit as st
import pandas as pd
from datetime import datetime
import os
import unicodedata
import re
import matplotlib.pyplot as plt
import base64

# ===============================
# FUNÇÕES AUXILIARES
# ===============================
def normalizar(nome):
    nome = unicodedata.normalize("NFKD", str(nome))
    nome = "".join(c for c in nome if not unicodedata.combining(c))
    return nome.strip().lower()

def extrair_nome_item(qr_texto):
    try:
        partes = qr_texto.split(" ")
        for i, parte in enumerate(partes):
            if parte.lower() == "nome" and i+4 < len(partes):
                return partes[i+4].strip()
    except Exception:
        return None

# ===============================
# LOGIN
# ===============================
usuarios = {
    "colaborador": {"senha": "1234", "perfil": "colaborador"},
    "portaria": {"senha": "1234", "perfil": "portaria"},
    "admin": {"senha": "admin", "perfil": "admin"},
    "supervisor": {"senha": "sup123", "perfil": "supervisor"}
}

def login_sidebar():
    st.sidebar.title("Login")

    if "logado" in st.session_state and st.session_state["logado"]:
        st.sidebar.markdown(f"👤 **Usuário:** {st.session_state['usuario']}")
        if st.sidebar.button("Sair"):
            st.session_state.clear()
            st.success("Você saiu do sistema.")
            st.stop()
    else:
        with st.sidebar.form("form_login"):
            username = st.text_input("Usuário:")
            password = st.text_input("Senha:", type="password")
            login_btn = st.form_submit_button("Entrar")

        if login_btn:
            if username in usuarios and password == usuarios[username]["senha"]:
                st.session_state["logado"] = True
                st.session_state["usuario"] = username
                st.session_state["perfil"] = usuarios[username]["perfil"]
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos!")
                st.stop()

    if "logado" not in st.session_state or not st.session_state["logado"]:
        st.info("Faça login para acessar o sistema.")
        st.stop()

# ===============================
# ARQUIVOS CSV
# ===============================
ATIVOS_FILE = "ativos_glpi.csv"
SAIDA_FILE = "saida_equipamentos.csv"
DASHBOARD_FILE = "saida_dashboard.csv"

# ===============================
# TELA SUPERVISOR
# ===============================
def tela_supervisor():
    st.header("🕵️ Supervisor - Autorização de Saídas")

    if not os.path.exists(SAIDA_FILE):
        st.info("Nenhum registro de saída encontrado.")
        st.stop()

    df = pd.read_csv(SAIDA_FILE, dtype=str)
    df.columns = [normalizar(c) for c in df.columns]

    if "autorizado" not in df.columns:
        df["autorizado"] = ""
    if "supervisor" not in df.columns:
        df["supervisor"] = ""
    if "numero de serie" not in df.columns:
        st.error("❌ A coluna 'Número de Série' não foi encontrada no CSV de saídas!")
        st.stop()

    pendentes = df[df["autorizado"].isna() | (df["autorizado"].str.strip() == "")]
    if pendentes.empty:
        st.success("Não há solicitações pendentes para autorização.")
        return

    for idx, row in pendentes.iterrows():
        st.markdown(
            f"**Colaborador:** {row.get('colaborador','')}  \n"
            f"**Destino:** {row.get('destino','')}  \n"
            f"**Setor:** {row.get('setor','')}  \n"
            f"**Número de Série:** {row.get('numero de serie','')}  \n"
            f"**Data:** {row.get('data saida','')}"
        )

        with st.form(key=f"form_aut_{row['numero de serie']}_{idx}"):
            nome_gestor = st.text_input(
                "Digite seu nome para autorizar/negar:",
                key=f"sup_nome_{row['numero de serie']}_{idx}"
            )
            col1, col2 = st.columns(2)
            autorizado_btn = col1.form_submit_button(f"Autorizado")
            negado_btn = col2.form_submit_button(f"Negado")

            if autorizado_btn or negado_btn:
                if not nome_gestor.strip():
                    st.warning("⚠️ Você deve digitar seu nome antes de autorizar/negar.")
                else:
                    df.at[idx, "autorizado"] = "Sim" if autorizado_btn else "Não"
                    df.at[idx, "supervisor"] = nome_gestor
                    df.to_csv(SAIDA_FILE, index=False, encoding="utf-8-sig")

                    if autorizado_btn:
                        st.success(f"✅ Saída autorizada para {row.get('colaborador')} pelo gestor {nome_gestor}")
                    else:
                        st.error(f"❌ Saída negada para {row.get('colaborador')} pelo gestor {nome_gestor}")

# ===============================
# TELA COLABORADOR
# ===============================
def tela_colaborador():
    st.header("📤 Liberação Saída de Equipamentos")

    if os.path.exists(ATIVOS_FILE):
        ativos_df = pd.read_csv(ATIVOS_FILE, dtype=str, sep=";", encoding="utf-8")
        st.success("✅ Lista de ativos carregada automaticamente!")
    else:
        csv_file = st.file_uploader("Envie o CSV do GLPI:", type=["csv"])
        if csv_file:
            ativos_df = pd.read_csv(csv_file, dtype=str, sep=";", encoding="utf-8")
            ativos_df.to_csv(ATIVOS_FILE, index=False, sep=";", encoding="utf-8-sig")
            st.success("Arquivo salvo para uso futuro!")
        else:
            st.stop()

    ativos_df.columns = [normalizar(c) for c in ativos_df.columns]
    obrigatorias = ["numero de serie","nome","nome alternativo do usuario"]
    for col in obrigatorias:
        if col not in ativos_df.columns:
            st.error(f"❌ O arquivo deve conter a coluna '{col}'.")
            st.stop()

    tipo_form = st.radio(
        "Escolha o tipo de formulário:",
        ["Formulário com QR Code", "Formulário Manual sem QR Code"]
    )

    # --- Formulário QR Code ---
    if tipo_form == "Formulário com QR Code":
        st.subheader("📲 Formulário de Saída de Equipamento (QR Code)")

        with st.form("form_saida_qr"):
            qr_texto = st.text_input("Escaneie o QR Code ou digite o texto do QR Code:")
            info_ativo = None
            nome_usuario = ""
            colaborador = ""

            if qr_texto:
                nome_item = extrair_nome_item(qr_texto)
                if nome_item:
                    padrao = f"^{re.escape(nome_item)}"
                    encontrado = ativos_df[ativos_df["nome"].str.match(padrao, case=False, na=False)]
                    if not encontrado.empty:
                        info_ativo = encontrado.iloc[0]
                        st.success(f"✅ Equipamento encontrado: {info_ativo.get('nome alternativo do usuario','N/A')}")
                        nome_usuario = info_ativo.get("nome alternativo do usuario","")
                        colaborador = info_ativo.get("usuario","")
                    else:
                        st.warning("⚠️ Equipamento não encontrado no GLPI.")
                else:
                    st.warning("⚠️ Não foi possível extrair o 'Nome do item' do QR Code.")

            nome_usuario = st.text_input("Usuário:", value=nome_usuario)
            colaborador = st.text_input("Colaborador:", value=colaborador)
            setor = st.selectbox("Setor:", ["TI","Financeiro","Logística","Qualidade","RH","Contabilidade","Compras"])
            destino = st.text_area("Destino:")

            enviar = st.form_submit_button("Registrar Saída")

        if enviar:
            if not colaborador or not destino:
                st.warning("⚠️ Preencha todos os campos obrigatórios.")
            else:
                data_saida = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                registro = {
                    "Data Saída": data_saida,
                    "Número de Série": info_ativo.get("numero de serie","").upper() if info_ativo else "",
                    "Nome do Item": info_ativo.get("nome","") if info_ativo else "",
                    "Nome Usuário": nome_usuario,
                    "Setor": setor,
                    "Colaborador": colaborador,
                    "Destino": destino,
                    "Confirmado": "Não",
                    "Autorizado": "",
                    "Supervisor": "",
                    "Entrada": ""
                }
                if os.path.exists(SAIDA_FILE):
                    df_saida = pd.read_csv(SAIDA_FILE, dtype=str)
                    df_saida.columns = [normalizar(c) for c in df_saida.columns]
                    novo = pd.DataFrame([registro])
                    novo.columns = [normalizar(c) for c in novo.columns]
                    df_saida = pd.concat([df_saida, novo], ignore_index=True)
                    df_saida = df_saida.loc[:, ~df_saida.columns.duplicated()]
                else:
                    df_saida = pd.DataFrame([registro])

                df_saida.to_csv(SAIDA_FILE, index=False, encoding="utf-8-sig")

                # Atualiza CSV para dashboard
                if os.path.exists(DASHBOARD_FILE):
                    df_dash = pd.read_csv(DASHBOARD_FILE, dtype=str)
                    df_dash = pd.concat([df_dash, pd.DataFrame([registro])], ignore_index=True)
                else:
                    df_dash = pd.DataFrame([registro])
                df_dash.to_csv(DASHBOARD_FILE, index=False, encoding="utf-8-sig")

                st.success("✅ Solicitação registrada com sucesso!")

    # --- Formulário Manual ---
    else:
        st.subheader("📄 Formulário de Saída Manual (Sem QR Code)")

        nome_busca = st.text_input("Digite o nome do usuário para pesquisar:")

        if "equipamento_selecionado" not in st.session_state:
            st.session_state["equipamento_selecionado"] = None
        if "colaborador_pesquisa" not in st.session_state:
            st.session_state["colaborador_pesquisa"] = ""

        if st.button("Pesquisar Equipamento", key="pesquisar_manual"):
            if nome_busca.strip() == "":
                st.warning("⚠️ Digite um nome para pesquisar.")
            else:
                ativos_df["nome_alt_normalizado"] = (
                    ativos_df["nome alternativo do usuario"]
                    .astype(str)
                    .apply(lambda x: unicodedata.normalize("NFKD", x).encode("ascii", errors="ignore").decode("utf-8").lower())
                )
                nome_proc = unicodedata.normalize("NFKD", nome_busca.strip()).encode("ascii", errors="ignore").decode("utf-8").lower()
                resultados = ativos_df[ativos_df["nome_alt_normalizado"].str.contains(nome_proc, na=False)]

                if resultados.empty:
                    st.error("❌ Nenhum resultado encontrado para esse nome.")
                else:
                    st.success(f"✅ {len(resultados)} resultado(s) encontrado(s):")
                    st.dataframe(resultados[["numero de serie","nome","nome alternativo do usuario"]].reset_index(drop=True))

                    key_usuario = f"selec_usuario_{nome_busca}"
                    escolha = st.selectbox("Selecione o usuário correspondente:", resultados["nome alternativo do usuario"].unique().tolist(), key=key_usuario)
                    st.session_state["equipamento_selecionado"] = resultados[resultados["nome alternativo do usuario"] == escolha].iloc[0].to_dict()
                    st.session_state["colaborador_pesquisa"] = nome_busca

        equipamento = st.session_state.get("equipamento_selecionado") or {}

        with st.form("form_saida_manual"):
            nome_usuario = st.text_input("Usuário:", value=equipamento.get("nome alternativo do usuario",""))
            colaborador = st.text_input("Colaborador:", value=st.session_state.get("colaborador_pesquisa",""))
            setor = st.selectbox("Setor:", ["TI","Financeiro","Logística","Qualidade","RH","Contabilidade","Compras"])
            destino = st.text_area("Destino:")

            enviar_manual = st.form_submit_button("Registrar Saída")

        if enviar_manual:
            if not colaborador or not destino:
                st.warning("⚠️ Preencha todos os campos obrigatórios.")
            else:
                data_saida = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                registro = {
                    "Data Saída": data_saida,
                    "Número de Série": equipamento.get("numero de serie","").upper(),
                    "Nome do Item": equipamento.get("nome",""),
                    "Nome Usuário": nome_usuario,
                    "Setor": setor,
                    "Colaborador": colaborador,
                    "Destino": destino,
                    "Confirmado": "Não",
                    "Autorizado": "",
                    "Supervisor": "",
                    "Entrada": ""
                }
                if os.path.exists(SAIDA_FILE):
                    df_saida = pd.read_csv(SAIDA_FILE, dtype=str)
                    df_saida.columns = [normalizar(c) for c in df_saida.columns]
                    novo = pd.DataFrame([registro])
                    novo.columns = [normalizar(c) for c in novo.columns]
                    df_saida = pd.concat([df_saida, novo], ignore_index=True)
                    df_saida = df_saida.loc[:, ~df_saida.columns.duplicated()]
                else:
                    df_saida = pd.DataFrame([registro])

                df_saida.to_csv(SAIDA_FILE, index=False, encoding="utf-8-sig")

                # Atualiza CSV para dashboard
                if os.path.exists(DASHBOARD_FILE):
                    df_dash = pd.read_csv(DASHBOARD_FILE, dtype=str)
                    df_dash = pd.concat([df_dash, pd.DataFrame([registro])], ignore_index=True)
                else:
                    df_dash = pd.DataFrame([registro])
                df_dash.to_csv(DASHBOARD_FILE, index=False, encoding="utf-8-sig")

                st.success("✅ Solicitação registrada com sucesso!")

# ===============================
# TELA PORTARIA
# ===============================
def tela_portaria():
    st.header("🛂 Portaria - Confirmação de Saída / Registro de Entrada")

    if not os.path.exists(SAIDA_FILE):
        st.info("Nenhum registro de saída encontrado.")
        st.stop()

    df = pd.read_csv(SAIDA_FILE, dtype=str)
    df.columns = [normalizar(c) for c in df.columns]

    # Colunas essenciais
    for col in ["confirmado", "autorizado", "entrada"]:
        if col not in df.columns:
            df[col] = "Não"

    # -----------------------------
    # CONFIRMAÇÃO DE SAÍDA
    # -----------------------------
    st.subheader("📤 Confirmação de Saídas")
    pendentes_saida = df[(df["confirmado"]=="Não")]

    if pendentes_saida.empty:
        st.success("Não há saídas pendentes.")
    else:
        for idx, row in pendentes_saida.iterrows():
            st.markdown(
                f"**Colaborador:** {row.get('colaborador','')}  \n"
                f"**Destino:** {row.get('destino','')}  \n"
                f"**Setor:** {row.get('setor','')}  \n"
                f"**Número de Série:** {row.get('numero de serie','')}  \n"
                f"**Data:** {row.get('data saida','')}"
            )

            autorizado = row.get("autorizado","")
            if autorizado=="Sim":
                if st.button(f"Confirmar saída - {row.get('colaborador','---')}", key=f"conf_{idx}"):
                    df.at[idx,"confirmado"]="Sim"
                    df.to_csv(SAIDA_FILE, index=False, encoding="utf-8-sig")
                    st.success(f"✅ Saída de {row.get('colaborador')} confirmada!")
                    st.rerun()
            elif autorizado=="Não":
                st.error("❌ Saída Negada pelo Supervisor")
            else:
                st.info("⏳ Aguardando autorização do Supervisor")

    # -----------------------------
    # REGISTRO DE ENTRADA
    # -----------------------------
    st.subheader("✅ Registrar Entrada de Equipamento")
    # Equipamentos que já saíram e ainda não entraram
    equipamentos_para_entrada = df[(df["confirmado"]=="Sim") & (df["entrada"]!="Sim")]["numero de serie"].unique().tolist()

    if equipamentos_para_entrada:
        selected_pc = st.selectbox("Selecione o computador:", equipamentos_para_entrada)
        st.button("Registrar Entrada (Desativado Temporariamente)", disabled=True)
        #st.info("⚠️ O registro de entrada está temporariamente desativado pela administração.")
        if st.button("Registrar Entrada", key="btn_entrada"):
             last_idx = df[df["numero de serie"]==selected_pc].index[-1]
             df.at[last_idx,"entrada"]="Sim"
             df.to_csv(SAIDA_FILE, index=False, encoding="utf-8-sig")
             st.success(f"💻 Entrada do computador {selected_pc} registrada!")
             st.rerun()
    else:
        st.info("Nenhum equipamento pendente para entrada.")
        #st.info("⚠️ O registro de entrada está temporariamente desativado pela administração.")

# ===============================
# TELA DASHBOARD
# ===============================
def tela_dashboard():
    st.header("📊 Dashboard de Saídas")

    if not os.path.exists(DASHBOARD_FILE):
        st.info("Nenhum registro encontrado.")
        return

    df_dashboard = pd.read_csv(DASHBOARD_FILE, dtype=str)
    df_dashboard.columns = [normalizar(c) for c in df_dashboard.columns]

    for col in ["confirmado", "autorizado", "supervisor", "colaborador", "setor"]:
        if col not in df_dashboard.columns:
            df_dashboard[col] = ""

    total_saidas = len(df_dashboard)
    total_confirmadas = len(df_dashboard[df_dashboard["confirmado"] == "Sim"])
    total_pendentes = len(df_dashboard[df_dashboard["confirmado"] == "Não"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Saídas", total_saidas)
    col2.metric("Confirmadas", total_confirmadas)
    col3.metric("Pendentes", total_pendentes)

    st.markdown("---")

    if "mostrar_setor" not in st.session_state:
        st.session_state.mostrar_setor = False
    if "mostrar_supervisor" not in st.session_state:
        st.session_state.mostrar_supervisor = False
    if "mostrar_colaborador" not in st.session_state:
        st.session_state.mostrar_colaborador = False

    if st.button("👁️ Mostrar/Ocultar Todos os Dashboards", key="btn_geral_dashboard"):
        mostrar_todos = not (
            st.session_state.mostrar_setor
            or st.session_state.mostrar_supervisor
            or st.session_state.mostrar_colaborador
        )
        st.session_state.mostrar_setor = mostrar_todos
        st.session_state.mostrar_supervisor = mostrar_todos
        st.session_state.mostrar_colaborador = mostrar_todos

    col_a, col_b, col_c = st.columns(3)

    # Saídas por setor
    with col_a:
        if st.button("🏢 Setor", key="btn_setor_dashboard"):
            st.session_state["mostrar_setor"] = not st.session_state["mostrar_setor"]
        if st.session_state.mostrar_setor:
            if "setor" in df_dashboard.columns and not df_dashboard["setor"].dropna().empty:
                setor_counts = df_dashboard["setor"].value_counts()
                fig, ax = plt.subplots(figsize=(4, 3))
                ax.bar(setor_counts.index, setor_counts.values, color="#4C72B0")
                ax.set_title("Saídas por Setor")
                ax.set_xlabel("Setor")
                ax.set_ylabel("Qtd")
                plt.xticks(rotation=45)
                st.pyplot(fig)

    # Autorizações por supervisor
    with col_b:
        if st.button("🕵️ Supervisor", key="btn_supervisor_dashboard_col"):
            st.session_state["mostrar_supervisor"] = not st.session_state["mostrar_supervisor"]
        if st.session_state.mostrar_supervisor:
            if "supervisor" in df_dashboard.columns and not df_dashboard["supervisor"].dropna().empty:
                sup_counts = df_dashboard[df_dashboard["autorizado"] == "Sim"]["supervisor"].value_counts()
                fig, ax = plt.subplots(figsize=(4, 3))
                ax.bar(sup_counts.index, sup_counts.values, color="#55A868")
                ax.set_title("Autorizações por Supervisor")
                ax.set_xlabel("Supervisor")
                ax.set_ylabel("Autorizações")
                plt.xticks(rotation=45)
                st.pyplot(fig)

    # Autorizações por colaborador
    with col_c:
        if st.button("👤 Colaborador", key="btn_colaborador_dashboard_col"):
            st.session_state["mostrar_colaborador"] = not st.session_state["mostrar_colaborador"]
        if st.session_state.mostrar_colaborador:
            if "colaborador" in df_dashboard.columns and not df_dashboard["colaborador"].dropna().empty:
                colab_counts = df_dashboard["autorizado"].value_counts()
                fig, ax = plt.subplots(figsize=(4, 3))
                ax.bar(colab_counts.index, colab_counts.values, color="#C44E52")
                ax.set_title("Autorizações por Colaborador")
                ax.set_xlabel("Colaborador")
                ax.set_ylabel("Autorizações")
                plt.xticks(rotation=45)
                st.pyplot(fig)

# ===============================
# EXECUÇÃO PRINCIPAL
# ===============================
st.set_page_config(
    page_title="Liberação Saída de Equipamentos",
    layout="centered"
)

# ===============================
# LOGO DA EMPRESA (da pasta templates)
# ===============================
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.image("templates/234x234.png", width=200)

# ===============================
# TÍTULO PRINCIPAL
# ===============================
st.title("Sistema de Liberação Saída de Equipamentos")
st.markdown("Bem-vindo ao sistema de controle de saída de equipamentos da sua empresa.")

login_sidebar()
perfil = st.session_state["perfil"]

if perfil=="colaborador":
    tela_colaborador()
elif perfil=="portaria":
    tela_portaria()
elif perfil=="supervisor":
    tela_supervisor()
elif perfil=="admin":
    menu = st.sidebar.radio("Menu", ["Liberação Saída","Portaria","Supervisor","Dashboard","Log"])
    if menu=="Liberação Saída":
        tela_colaborador()
    elif menu=="Portaria":
        tela_portaria()
    elif menu=="Supervisor":
        tela_supervisor()
    elif menu=="Dashboard":
        tela_dashboard()

# ===============================
# LOG DE SAÍDAS (ADMIN e COLABORADOR)
# ===============================
if perfil in ["admin"] and os.path.exists(SAIDA_FILE):
    st.subheader("📜 Log de liberações registradas")
    df_log = pd.read_csv(SAIDA_FILE,dtype=str)
    st.dataframe(df_log.sort_values(by=df_log.columns[0],ascending=False))
