import pandas as pd
import plotly.express as px
import streamlit as st

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Dashboard de Assinaturas",
    page_icon=":bar_chart:",
    layout="wide"
)

# FUNÇÃO PARA CARREGAR OS DADOS DA NOVA PLANILHA
@st.cache_data
def get_data_from_excel():
    df = pd.read_excel(
        io=r'C:\Users\Pedro\Documents\portfolio\dio-heineken-bootcamp-dashboard-excel\database.xlsx',
        engine='openpyxl',
        sheet_name=0
    )
    df.rename(columns=lambda x: x.strip().replace('\n', ' '), inplace=True)
    return df

df = get_data_from_excel()

# Converter colunas de preço para numérico
df["EA Play Season Pass Price"] = pd.to_numeric(df["EA Play Season Pass Price"], errors='coerce')
df["Minecraft Season Pass Price"] = pd.to_numeric(df["Minecraft Season Pass Price"], errors='coerce')

# SIDEBAR PARA FILTROS
st.sidebar.header("Por favor, filtre aqui:")
assinatura_tipo = st.sidebar.multiselect("Selecione o Tipo de Assinatura:", options=df["Subscription Type"].unique(), default=df["Subscription Type"].unique())
renovacao_auto = st.sidebar.multiselect("Renovação Automática:", options=df["Auto Renewal"].unique(), default=df["Auto Renewal"].unique())
df_selection = df.query("`Subscription Type` == @assinatura_tipo & `Auto Renewal` == @renovacao_auto")

# PÁGINA PRINCIPAL
st.title(":bar_chart: Dashboard de Assinaturas")
st.markdown("##")

# 1. Quantos assinantes existem atualmente?
st.subheader("1. Quantos assinantes existem atualmente?")
total_assinantes = df_selection["Subscriber ID"].nunique()
st.metric(label="Total de Assinantes", value=total_assinantes)

# 2. Qual é a receita total gerada pelas assinaturas?
st.subheader("2. Receita Total Gerada pelas Assinaturas")
total_receita = df_selection["Total Value"].sum()
st.metric(label="Receita Total", value=f"R$ {total_receita:.2f}")

# 3. Qual é a receita gerada pelo EA Play Season Pass?
st.subheader("3. Receita Gerada pelo EA Play Season Pass")
if "EA Play Season Pass Price" in df_selection.columns:
    receita_ea_play = df_selection["EA Play Season Pass Price"].sum()
    st.metric(label="Receita EA Play Season Pass", value=f"R$ {receita_ea_play:.2f}")
else:
    st.warning("Coluna 'EA Play Season Pass Price' não encontrada no dataset.")

# 4. Qual é a receita gerada pelo Minecraft Season Pass?
st.subheader("4. Receita Gerada pelo Minecraft Season Pass")
if "Minecraft Season Pass Price" in df_selection.columns:
    receita_minecraft = df_selection["Minecraft Season Pass Price"].sum()
    st.metric(label="Receita Minecraft Season Pass", value=f"R$ {receita_minecraft:.2f}")
else:
    st.warning("Coluna 'Minecraft Season Pass Price' não encontrada no dataset.")

# 5. Qual é a receita média por assinante com e sem cupons aplicados?
st.subheader("5. Receita Média por Assinante com e sem Cupons Aplicados")
df_selection["Usou Cupons"] = df_selection["Coupon Value"].apply(lambda x: "Sim" if x > 0 else "Não")
receita_media_cupons = df_selection.groupby("Usou Cupons")["Total Value"].mean().reset_index()
receita_media_cupons.columns = ["Usou Cupons", "Receita Média"]
st.dataframe(receita_media_cupons)
fig_receita_media_cupons = px.bar(receita_media_cupons, x="Usou Cupons", y="Receita Média", title="Receita Média por Assinante com e sem Cupons Aplicados", color_discrete_sequence=["#9b59b6"])
st.plotly_chart(fig_receita_media_cupons)

# 6. Qual é o valor total de cupons aplicados?
st.subheader("6. Valor Total de Cupons Aplicados")
total_cupons = df_selection["Coupon Value"].sum()
st.metric(label="Valor Total de Cupons", value=f"R$ {total_cupons:.2f}")

# 7. Qual é a distribuição dos assinantes por tipo de assinatura?
st.subheader("7. Distribuição dos Assinantes por Tipo de Assinatura")
assinantes_por_tipo = df_selection["Subscription Type"].value_counts().reset_index()
assinantes_por_tipo.columns = ["Tipo de Assinatura", "Número de Assinantes"]
st.dataframe(assinantes_por_tipo)
fig_assinantes_por_tipo = px.bar(assinantes_por_tipo, x="Tipo de Assinatura", y="Número de Assinantes", title="Distribuição dos Assinantes por Tipo de Assinatura", color_discrete_sequence=["#9b59b6"])
st.plotly_chart(fig_assinantes_por_tipo)

# 8. Qual é a receita média por tipo de plano?
st.subheader("8. Receita Média por Tipo de Plano")
receita_media_plano = df_selection.groupby("Plan")["Total Value"].mean().reset_index()
receita_media_plano.columns = ["Plano", "Receita Média"]
st.dataframe(receita_media_plano)
fig_receita_media_plano = px.bar(receita_media_plano, x="Plano", y="Receita Média", title="Receita Média por Tipo de Plano", color_discrete_sequence=["#9b59b6"])
st.plotly_chart(fig_receita_media_plano)

# 9. Qual é a média de preço das assinaturas?
st.subheader("9. Média de Preço das Assinaturas")
media_preco = df_selection["Subscription Price"].mean()
st.metric(label="Preço Médio da Assinatura", value=f"R$ {media_preco:.2f}")

# 10. Qual é a taxa de retenção de assinantes ao longo do tempo?
st.subheader("10. Taxa de Retenção de Assinantes ao Longo do Tempo")
df_selection['Start Date'] = pd.to_datetime(df_selection['Start Date'])
assinantes_por_data = df_selection.groupby(df_selection['Start Date'].dt.to_period('M')).size().reset_index(name='Número de Assinantes')
assinantes_por_data['Start Date'] = assinantes_por_data['Start Date'].dt.to_timestamp()
fig_assinantes_por_data = px.line(assinantes_por_data, x='Start Date', y='Número de Assinantes', title="Taxa de Retenção de Assinantes ao Longo do Tempo", color_discrete_sequence=["#9b59b6"])
st.plotly_chart(fig_assinantes_por_data)

# ESCONDER ESTILO PADRÃO DO STREAMLIT
hide_st_style = """
            <style>
            #MainMenu {visibility:hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)