import io
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(
    page_title="Dashboard de Assinaturas",
    page_icon=":bar_chart:",
    layout="wide"
)

REPO_DB_FILENAME = Path("database.xlsx")
EXCEL_COLS = [
    "Subscriber ID", "Name", "Plan", "Start Date", "Auto Renewal", "Subscription Price",
    "Subscription Type", "EA Play Season Pass", "EA Play Season Pass Price",
    "Minecraft Season Pass", "Minecraft Season Pass Price", "Coupon Value", "Total Value"
]

def clean_col(c):
    return c.strip().replace('\n', ' ')

@st.cache_data(show_spinner=False)
def load_excel_from_bytes(content: bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    df.rename(columns=clean_col, inplace=True)
    return df

@st.cache_data(show_spinner=False)
def load_data_from_path(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    df.rename(columns=clean_col, inplace=True)
    return df

def get_dataframe(uploaded_file, url_input: str = None):
    df = None
    if uploaded_file is not None:
        try:
            content = uploaded_file.read()
            df = load_excel_from_bytes(content)
        except Exception as e:
            st.error(f"Erro ao ler arquivo enviado: {e}")
            st.stop()
    elif url_input:
        import requests
        try:
            resp = requests.get(url_input, timeout=30)
            resp.raise_for_status()
            df = load_excel_from_bytes(resp.content)
        except Exception as e:
            st.error(f"Erro ao baixar/ler URL: {e}")
            st.stop()
    elif REPO_DB_FILENAME.exists():
        try:
            df = load_data_from_path(REPO_DB_FILENAME)
        except Exception as e:
            st.error(f"Erro ao ler {REPO_DB_FILENAME}: {e}")
            st.stop()
    else:
        st.warning("Nenhum arquivo fornecido. Faça upload, informe uma URL, ou coloque 'database.xlsx' na raiz do projeto.")
        st.stop()
    df.columns = [clean_col(c) for c in df.columns]
    missing = [c for c in EXCEL_COLS if c not in df.columns]
    if missing:
        st.error(f"Colunas obrigatórias faltando: {missing}")
        st.stop()
    return df

# ========== UX DE FONTE ==========
with st.sidebar:
    uploaded_file = st.file_uploader(
        "Faça upload do Excel (.xlsx)",
        type=["xlsx"]
    )
    url_input = st.text_input("Ou cole uma URL direta para o arquivo .xlsx (http/https)", "")

st.info(
    "Somente arquivos no formato padrão da planilha de assinaturas XBOX Game Pass "
    "('Subscriber ID', 'Plan', 'Start Date', etc.) do Bootcamp DIO/Heineken são compatíveis. "
    "Planilhas com estrutura diferente não serão processadas."
)

df = get_dataframe(uploaded_file, url_input.strip() or None)

# Conversão numérica
for col in [
    "EA Play Season Pass Price", "Minecraft Season Pass Price",
    "Subscription Price", "Coupon Value", "Total Value"
]:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')

# ========== SIDEBAR: FILTROS ==========
st.sidebar.header("Por favor, filtre aqui:")
assinatura_tipo = st.sidebar.multiselect(
    "Selecione o Tipo de Assinatura:", 
    options=df["Subscription Type"].dropna().unique(), 
    default=list(df["Subscription Type"].dropna().unique())
)
renovacao_auto = st.sidebar.multiselect(
    "Renovação Automática:", 
    options=df["Auto Renewal"].dropna().unique(), 
    default=list(df["Auto Renewal"].dropna().unique())
)

# Filtro robusto
df_selection = df[
    df["Subscription Type"].isin(assinatura_tipo) &
    df["Auto Renewal"].isin(renovacao_auto)
].copy()

# ==================== KPIs ====================
st.title(":bar_chart: Dashboard de Assinaturas")
st.markdown("##")

### 📊 1. KPIs de Receita & Valor
st.header("📊 KPIs de Receita & Valor")

col1, col2, col3, col4 = st.columns(4)

# Receita total mensal/anual
# CORREÇÃO: Convertendo período para string antes de calcular métricas
df_selection['Month'] = df_selection['Start Date'].dt.to_period('M').astype(str)
df_selection['Year'] = df_selection['Start Date'].dt.to_period('Y').astype(str)

receita_mensal = df_selection.groupby('Month')["Total Value"].sum()
receita_anual = df_selection.groupby('Year')["Total Value"].sum()

col1.metric("Receita Total Mensal (último mês)", f"R$ {receita_mensal.iloc[-1]:.2f}" if not receita_mensal.empty else "N/A")
col2.metric("Receita Total Anual (último ano)", f"R$ {receita_anual.iloc[-1]:.2f}" if not receita_anual.empty else "N/A")

# ARPU
arpu = df_selection["Total Value"].sum() / max(df_selection["Subscriber ID"].nunique(), 1)
col3.metric("Receita Média por Usuário (ARPU)", f"R$ {arpu:.2f}")

# Desconto Médio por Cupom
avg_coupon = df_selection["Coupon Value"].mean()
col4.metric("Desconto Médio por Cupom", f"R$ {avg_coupon:.2f}")

col5, col6 = st.columns([2,2])

# Receita por Plano
receita_plano = df_selection.groupby("Plan")["Total Value"].sum().reset_index()
col5.subheader("Receita por Plano")
col5.dataframe(receita_plano, height=180)

# Contribuição Add-ons
ea_play_sum = df_selection["EA Play Season Pass Price"].sum()
minecraft_sum = df_selection["Minecraft Season Pass Price"].sum()
total_value_sum = df_selection["Total Value"].sum()
contrib_addons = (ea_play_sum + minecraft_sum) / total_value_sum if total_value_sum > 0 else 0
col6.metric("Contribuição Add-ons (%)", f"{contrib_addons*100:.2f}%")

st.markdown("<hr>", unsafe_allow_html=True)

### 👥 2. KPIs de Base de Usuários
st.header("👥 KPIs de Base de Usuários")
colu1, colu2, colu3, colu4 = st.columns(4)

total_ativos = df_selection["Subscriber ID"].nunique()

# Crescimento mensal
if not df_selection['Month'].empty:
    crescimento_mes_df = df_selection.groupby('Month')["Subscriber ID"].nunique().reset_index()
    if len(crescimento_mes_df) > 1:
        crescimento_mes = crescimento_mes_df.iloc[-1]['Subscriber ID'] - crescimento_mes_df.iloc[-2]['Subscriber ID']
    else:
        crescimento_mes = crescimento_mes_df.iloc[0]['Subscriber ID'] if not crescimento_mes_df.empty else 0
else:
    crescimento_mes = 0

colu1.metric("Assinantes Ativos", total_ativos)
colu2.metric("Crescimento Mensal", int(crescimento_mes))

# Distribuição por Plano
plan_counts = df_selection["Plan"].value_counts()
plan_pct = (plan_counts / total_ativos * 100).round(1)
colu3.metric("Plano Mais Popular", plan_counts.idxmax() if not plan_counts.empty else "N/A")
colu4.metric("Plano Mais Popular (%)", f"{plan_pct.max() if not plan_pct.empty else 0}%")

# Auto Renovação
auto_yes = (df_selection["Auto Renewal"] == 'Yes').sum()
auto_pct = auto_yes / len(df_selection) * 100 if len(df_selection) > 0 else 0
churn = (df_selection["Auto Renewal"] == 'No').sum()
colu5, colu6 = st.columns(2)
colu5.metric("Taxa Auto Renovação (%)", f"{auto_pct:.2f}%")
colu6.metric("Churn Estimado", churn)

st.markdown("<hr>", unsafe_allow_html=True)

### 📈 3. KPIs de Engajamento & Produto
st.header("📈 KPIs de Engajamento & Produto")
n_total = len(df_selection)
ea_adoption = (df_selection["EA Play Season Pass"] == 'Yes').sum()
ea_pct = ea_adoption / n_total * 100 if n_total > 0 else 0
mc_adoption = (df_selection["Minecraft Season Pass"] == 'Yes').sum()
mc_pct = mc_adoption / n_total * 100 if n_total > 0 else 0

ticket_addons_df = df_selection[
    (df_selection["EA Play Season Pass"] == 'Yes') | 
    (df_selection["Minecraft Season Pass"] == 'Yes')
]
ticket_addons = ticket_addons_df["Total Value"].mean() if not ticket_addons_df.empty else 0

col1e, col2e, col3e = st.columns(3)
col1e.metric("Adoção EA Play (%)", f"{ea_pct:.2f}%")
col2e.metric("Adoção Minecraft (%)", f"{mc_pct:.2f}%")
col3e.metric("Ticket Médio com Add-ons", f"R$ {ticket_addons:.2f}" if not pd.isnull(ticket_addons) and ticket_addons > 0 else "N/A")

mix_tipo_ass = df_selection["Subscription Type"].value_counts(normalize=True).mul(100).round(1).reset_index()
mix_tipo_ass.columns = ["Tipo de Assinatura", "%"]
st.dataframe(mix_tipo_ass)

st.markdown("<hr>", unsafe_allow_html=True)

### 🗓️ 4. KPIs Temporais & Cohort
st.header("🗓️ KPIs Temporais & Cohorte")

# Receita por mês de início
# CORREÇÃO: Já temos a coluna 'Month' como string
receita_inicio_mes = df_selection.groupby('Month')["Total Value"].sum().reset_index()
receita_inicio_mes.columns = ["Mês de Início", "Receita"]
receita_inicio_mes = receita_inicio_mes.sort_values('Mês de Início')

st.subheader("Receita por Mês de Início")
st.dataframe(receita_inicio_mes)

# CORREÇÃO: Gráfico com eixo X como string (não Period)
fig_receita_inicio_mes = px.line(
    receita_inicio_mes, x="Mês de Início", y="Receita",
    title="Receita por Mês de Início",
    color_discrete_sequence=["#F48C06"],
    markers=True
)
fig_receita_inicio_mes.update_layout(
    xaxis_title="Mês de Início",
    yaxis_title="Receita (R$)",
    xaxis_tickangle=-45
)
st.plotly_chart(fig_receita_inicio_mes, use_container_width=True)

# Sazonalidade (por trimestre)
# CORREÇÃO: Converter trimestre para string
df_selection['Quarter'] = df_selection['Start Date'].dt.to_period('Q').astype(str)
receita_trimestral = df_selection.groupby('Quarter')["Total Value"].sum().reset_index()
receita_trimestral.columns = ["Trimestre", "Receita"]
receita_trimestral = receita_trimestral.sort_values('Trimestre')

st.subheader("Receita Trimestral")
st.dataframe(receita_trimestral)

fig_receita_trimestre = px.line(
    receita_trimestral, x="Trimestre", y="Receita",
    title="Receita Trimestral/Sazonalidade",
    color_discrete_sequence=["#6a4c93"],
    markers=True
)
fig_receita_trimestre.update_layout(
    xaxis_title="Trimestre",
    yaxis_title="Receita (R$)",
    xaxis_tickangle=-45
)
st.plotly_chart(fig_receita_trimestre, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

### 🎯 5. KPIs de Desempenho por Segmento
st.header("🎯 KPIs de Desempenho por Segmento")

valor_medio_plano = df_selection.groupby("Plan")["Total Value"].mean().reset_index()
valor_medio_plano.columns = ["Plano", "Valor Médio"]
valor_medio_plano["Valor Médio"] = valor_medio_plano["Valor Médio"].round(2)

auto_renovacao_plano = df_selection.groupby("Plan")["Auto Renewal"].apply(
    lambda s: (s == 'Yes').mean() * 100
).reset_index()
auto_renovacao_plano.columns = ["Plano", "Auto Renovação (%)"]
auto_renovacao_plano["Auto Renovação (%)"] = auto_renovacao_plano["Auto Renovação (%)"].round(2)

uso_cupom_plano = df_selection.groupby("Plan")["Coupon Value"].mean().reset_index()
uso_cupom_plano.columns = ["Plano", "Cupom Médio"]
uso_cupom_plano["Cupom Médio"] = uso_cupom_plano["Cupom Médio"].round(2)

col1k, col2k, col3k = st.columns(3)

with col1k:
    st.subheader("Valor Médio por Plano")
    st.dataframe(valor_medio_plano, height=200)

with col2k:
    st.subheader("Auto Renovação por Plano (%)")
    st.dataframe(auto_renovacao_plano, height=200)

with col3k:
    st.subheader("Cupom Médio por Plano")
    st.dataframe(uso_cupom_plano, height=200)

# Gráfico comparativo
fig_comparativo = make_subplots(
    rows=1, cols=3,
    subplot_titles=("Valor Médio por Plano", "Auto Renovação por Plano (%)", "Cupom Médio por Plano"),
    shared_yaxes=False
)

# Gráfico 1: Valor Médio
fig_comparativo.add_trace(
    go.Bar(
        x=valor_medio_plano["Plano"],
        y=valor_medio_plano["Valor Médio"],
        name="Valor Médio",
        marker_color='#1f77b4'
    ),
    row=1, col=1
)

# Gráfico 2: Auto Renovação
fig_comparativo.add_trace(
    go.Bar(
        x=auto_renovacao_plano["Plano"],
        y=auto_renovacao_plano["Auto Renovação (%)"],
        name="Auto Renovação (%)",
        marker_color='#2ca02c'
    ),
    row=1, col=2
)

# Gráfico 3: Cupom Médio
fig_comparativo.add_trace(
    go.Bar(
        x=uso_cupom_plano["Plano"],
        y=uso_cupom_plano["Cupom Médio"],
        name="Cupom Médio",
        marker_color='#ff7f0e'
    ),
    row=1, col=3
)

fig_comparativo.update_layout(
    height=400,
    showlegend=False,
    title_text="Comparativo de Desempenho por Plano"
)

st.plotly_chart(fig_comparativo, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

### 📉 6. KPIs de Eficiência Comercial
st.header("📉 KPIs de Eficiência Comercial")

df_selection['Usou Cupom'] = df_selection['Coupon Value'].apply(lambda x: x > 0)
df_com_cupom = df_selection[df_selection['Usou Cupom']]
df_sem_cupom = df_selection[~df_selection['Usou Cupom']]

valor_com_cupom = df_com_cupom['Total Value'].mean() if not df_com_cupom.empty else 0
valor_sem_cupom = df_sem_cupom['Total Value'].mean() if not df_sem_cupom.empty else 0

col1ec, col2ec = st.columns(2)
col1ec.metric("Ticket Médio com Cupom", f"R$ {valor_com_cupom:.2f}" if not pd.isnull(valor_com_cupom) and valor_com_cupom > 0 else "N/A")
col2ec.metric("Ticket Médio sem Cupom", f"R$ {valor_sem_cupom:.2f}" if not pd.isnull(valor_sem_cupom) and valor_sem_cupom > 0 else "N/A")

valor_liquido = df_selection['Total Value'].sum() - df_selection['Coupon Value'].sum()
st.metric("Valor Líquido após Cupom", f"R$ {valor_liquido:.2f}")

# Eficiência de Add-ons
assinaturas_com_addon = df_selection[
    (df_selection["EA Play Season Pass"] == 'Yes') | 
    (df_selection["Minecraft Season Pass"] == 'Yes')
]

if not assinaturas_com_addon.empty and assinaturas_com_addon['Subscription Price'].sum() > 0:
    efeic_addon = (assinaturas_com_addon['EA Play Season Pass Price'].sum() + 
                   assinaturas_com_addon['Minecraft Season Pass Price'].sum()) / assinaturas_com_addon['Subscription Price'].sum()
    st.metric("Eficiência de Add-ons", f"{efeic_addon*100:.2f}%")
else:
    st.metric("Eficiência de Add-ons", "N/A")

# Análise adicional: Comparação de retenção com/sem cupom
if not df_selection.empty:
    retencao_com_cupom = (df_com_cupom['Auto Renewal'] == 'Yes').mean() * 100 if not df_com_cupom.empty else 0
    retencao_sem_cupom = (df_sem_cupom['Auto Renewal'] == 'Yes').mean() * 100 if not df_sem_cupom.empty else 0
    
    col3ec, col4ec = st.columns(2)
    col3ec.metric("Retenção com Cupom (%)", f"{retencao_com_cupom:.2f}%" if retencao_com_cupom > 0 else "N/A")
    col4ec.metric("Retenção sem Cupom (%)", f"{retencao_sem_cupom:.2f}%" if retencao_sem_cupom > 0 else "N/A")

st.markdown("<hr>", unsafe_allow_html=True)

### 📊 7. Visualizações Adicionais
st.header("📊 Visualizações Adicionais")

# Distribuição de Planos
fig_planos = px.pie(
    df_selection, 
    names='Plan',
    title='Distribuição de Planos',
    hole=0.3,
    color_discrete_sequence=px.colors.qualitative.Set3
)
st.plotly_chart(fig_planos, use_container_width=True)

# Heatmap de Receita por Plano e Tipo de Assinatura
heatmap_data = df_selection.groupby(['Plan', 'Subscription Type'])['Total Value'].sum().unstack().fillna(0)
if not heatmap_data.empty:
    fig_heatmap = px.imshow(
        heatmap_data,
        title='Heatmap: Receita por Plano e Tipo de Assinatura',
        labels=dict(x="Tipo de Assinatura", y="Plano", color="Receita"),
        color_continuous_scale='Viridis',
        aspect="auto"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

### 📈 8. Insights e Recomendações
st.header("💡 Insights e Recomendações")

with st.expander("Clique para ver recomendações baseadas nos dados"):
    st.markdown("""
    ### Recomendações Estratégicas:
    
    1. **Foco em Planos de Maior Valor:** Priorize o plano Ultimate que gera mais receita.
    2. **Incentivo à Auto Renovação:** Desenvolva campanhas para converter assinantes com 'Auto Renewal = No'.
    3. **Otimização de Cupons:** Analise se cupons maiores realmente aumentam a retenção.
    4. **Upsell de Add-ons:** Aproveite a boa adoção de EA Play e Minecraft para criar novos pacotes.
    5. **Segmentação por Cohorte:** Monitore a retenção por coorte de entrada para identificar padrões.
    
    ### Próximos Passos Analíticos:
    - Implementar modelo de previsão de churn
    - Análise de clusterização de clientes
    - Testes A/B com diferentes valores de cupom
    - Análise de LTV (Lifetime Value) por segmento
    """)

st.markdown("<br><br>", unsafe_allow_html=True)

# ESCONDER ESTILO PADRÃO DO STREAMLIT
hide_st_style = """
        <style>
        #MainMenu {visibility:hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """
st.markdown(hide_st_style, unsafe_allow_html=True)