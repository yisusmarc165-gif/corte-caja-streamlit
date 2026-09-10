# -*- coding: utf-8 -*-
"""
SISTEMA DE CORTE DE CAJA DIARIO - VERSIONAL STREAMLIT
=======================================================================================
Requisitos previos:
    pip install streamlit reportlab requests
Ejecutar con:
    streamlit run app.py
"""

import json
import os
from datetime import datetime
import requests
import streamlit as st

# Librería para generación de PDF profesional
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

CONFIG_FILE = "sucursales_config.json"
DENOMINACIONES = [500, 200, 100, 50, 20]

# Configuración de la página en Streamlit
st.set_page_config(
    page_title="Corte de Caja Diario",
    page_icon="💵",
    layout="wide"
)

# ==========================================
# FUNCIONES BÁSICAS DE CONFIGURACIÓN Y CÁLCULO
# ==========================================
def cargar_configuracion():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_configuracion(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def calcular_totales(datos):
    # 1. EFECTIVO = Billetes + Terminal + Comidas + Otros Gastos + Monedas
    datos['efectivo'] = (datos['total_billetes'] + datos['terminal'] + 
                        datos['comidas'] + datos['otros_gastos'] + datos['monedas'])
    
    # 2. SUBTOTAL = Efectivo - Trabajadora - Renta - Comidas - Otros Gastos
    datos['subtotal'] = (datos['efectivo'] - datos['trabajadora'] - 
                         datos['renta'] - datos['comidas'] - datos['otros_gastos'])
    
    # 3. TOTAL A ENTREGAR AL DUEÑO (Billetes - Trabajadora - Renta)
    datos['total'] = datos['total_billetes'] - datos['trabajadora'] - datos['renta']

# ==========================================
# GENERADORES DE ARCHIVOS Y REPORTES
# ==========================================
def generar_txt_bytes(datos):
    """Genera el contenido del TXT en memoria para descarga."""
    diferencia = datos['efectivo'] - datos['sistema']
    if abs(diferencia) < 0.01:
        estado_cuadraje = "CAJA CUADRADA PERFECTAMENTE ($0.00)"
    elif diferencia > 0:
        estado_cuadraje = f"SOBRANTE EN CAJA: +${diferencia:.2f}"
    else:
        estado_cuadraje = f"FALTANTE EN CAJA: -${abs(diferencia):.2f}"

    contenido = f"""=============================================
            CORTE DE CAJA - {datos['sucursal']}
=============================================
FECHA/HORA:     {datos['fecha_impresion']}
_____________________________________________
USUARIO:        {datos['usuario']}
_____________________________________________
SISTEMA:        ${datos['sistema']:10.2f}
EFECTIVO:       ${datos['efectivo']:10.2f}
_____________________________________________
TERMINAL:       ${datos['terminal']:10.2f}
TRABAJADOR(A):  ${datos['trabajadora']:10.2f}
RENTA:          ${datos['renta']:10.2f}
COMIDAS:        ${datos['comidas']:10.2f}
OTROS GASTOS:   ${datos['otros_gastos']:10.2f}
MONEDAS:        ${datos['monedas']:10.2f}
---------------------------------------------
subtotal:       ${datos['subtotal']:10.2f}
=============================================

TOTAL:          ${datos['total']:10.2f}
=============================================
ESTADO:         {estado_cuadraje}
=============================================
"""
    return contenido.encode("utf-8")

def generar_pdf(datos, filename="reporte_corte.pdf"):
    """Genera un PDF y lo guarda localmente, retornando la ruta."""
    if not REPORTLAB_AVAILABLE:
        return None

    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold',
        fontSize=20, leading=24, textColor=colors.HexColor('#1E293B')
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle', parent=styles['Normal'], fontName='Helvetica',
        fontSize=10, leading=14, textColor=colors.HexColor('#64748B')
    )
    cell_style = ParagraphStyle(
        'Cell', parent=styles['Normal'], fontName='Helvetica',
        fontSize=10, leading=13, textColor=colors.HexColor('#334155')
    )
    cell_style_bold = ParagraphStyle('CellBold', parent=cell_style, fontName='Helvetica-Bold')

    diferencia = datos['efectivo'] - datos['sistema']
    if abs(diferencia) < 0.01:
        estado_txt = "CAJA CUADRADA PERFECTAMENTE ($0.00)"
        color_estado = colors.HexColor('#166534')
        bg_estado = colors.HexColor('#DCFCE7')
    elif diferencia > 0:
        estado_txt = f"SOBRANTE EN CAJA: +${diferencia:.2f}"
        color_estado = colors.HexColor('#9A3412')
        bg_estado = colors.HexColor('#FFEDD5')
    else:
        estado_txt = f"FALTANTE EN CAJA: -${abs(diferencia):.2f}"
        color_estado = colors.HexColor('#991B1B')
        bg_estado = colors.HexColor('#FEE2E2')

    story = [
        Paragraph(f"CORTE DE CAJA - {datos['sucursal']}", title_style),
        Paragraph(f"Fecha de Emisión: {datos['fecha_impresion']} | Atendido por: {datos['usuario']}", subtitle_style),
        Spacer(1, 15),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#CBD5E1'), spaceAfter=15)
    ]

    data_table = [
        [Paragraph("<b>CONCEPTO</b>", cell_style_bold), Paragraph("<b>MONTO ($)</b>", cell_style_bold)],
        [Paragraph("Venta Reportada (Sistema)", cell_style), Paragraph(f"${datos['sistema']:,.2f}", cell_style)],
        [Paragraph("Efectivo Total Recontado", cell_style), Paragraph(f"${datos['efectivo']:,.2f}", cell_style)],
        [Paragraph("Venta por Terminal (TPV)", cell_style), Paragraph(f"${datos['terminal']:,.2f}", cell_style)],
        [Paragraph("Pago a Trabajador(a)", cell_style), Paragraph(f"${datos['trabajadora']:,.2f}", cell_style)],
        [Paragraph("Pago de Renta", cell_style), Paragraph(f"${datos['renta']:,.2f}", cell_style)],
        [Paragraph("Gastos de Comidas", cell_style), Paragraph(f"${datos['comidas']:,.2f}", cell_style)],
        [Paragraph("Otros Gastos General", cell_style), Paragraph(f"${datos['otros_gastos']:,.2f}", cell_style)],
        [Paragraph("Monedas en Caja (Permanecen)", cell_style), Paragraph(f"${datos['monedas']:,.2f}", cell_style)],
        [Paragraph("<b>Subtotal Restante</b>", cell_style_bold), Paragraph(f"<b>${datos['subtotal']:,.2f}</b>", cell_style_bold)],
        [Paragraph("<b>TOTAL A ENTREGAR AL DUEÑO</b>", cell_style_bold), Paragraph(f"<b>${datos['total']:,.2f}</b>", cell_style_bold)],
    ]

    t = Table(data_table, colWidths=[320, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0,9), (-1,9), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,10), (-1,10), colors.HexColor('#E0F2FE')),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    estado_data = [
        [Paragraph(f"<b>DIAGNÓSTICO AUDITORÍA DE CAJA:</b><br/>{estado_txt}", ParagraphStyle(
            'EstadoText', parent=cell_style, textColor=color_estado, fontName='Helvetica-Bold', fontSize=11, leading=16
        ))]
    ]
    t_estado = Table(estado_data, colWidths=[520])
    t_estado.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_estado),
        ('BOX', (0,0), (-1,-1), 1, color_estado),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(t_estado)

    doc.build(story)
    return filename

def enviar_por_telegram(pdf_path, datos, token, chat_id):
    """Envía el PDF por Telegram Bot API."""
    if not token or not chat_id:
        return False, "Faltan las credenciales (Token o Chat ID)."

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    mensaje_caption = (
        f"📄 *CORTE DE CAJA - {datos['sucursal']}*\n"
        f"👤 Cajero: {datos['usuario']}\n"
        f"📅 Fecha: {datos['fecha_impresion']}\n"
        f"💵 Total a Entregar: *${datos['total']:,.2f}*\n"
        f"📊 Sistema: ${datos['sistema']:,.2f}"
    )

    try:
        with open(pdf_path, 'rb') as doc:
            files = {'document': doc}
            data = {'chat_id': chat_id, 'caption': mensaje_caption, 'parse_mode': 'Markdown'}
            response = requests.post(url, data=data, files=files, timeout=15)
            
        if response.status_code == 200:
            return True, "¡Reporte enviado exitosamente por Telegram!"
        else:
            return False, f"Error Telegram ({response.status_code}): {response.text}"
    except Exception as e:
        return False, f"Error de conexión: {str(e)}"

# ==========================================
# INTERFAZ DE USUARIO EN STREAMLIT
# ==========================================
def main():
    st.title("💵 Sistema de Corte de Caja Diario")
    st.markdown("Auditoría, cálculo automático, generación de reportes e integración con Telegram.")

    config = cargar_configuracion()

    # --- BARRA LATERAL (CONFIGURACIÓN) ---
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Guardar / Editar Renta por sucursal
        st.subheader("Rentas por Sucursal")
        sucursal_config = st.text_input("Nueva Sucursal / Editar", value="").upper().strip()
        renta_config = st.number_input("Renta fija ($)", min_value=0.0, step=100.0)
        
        if st.button("Guardar Configuración Renta"):
            if sucursal_config:
                config[sucursal_config] = renta_config
                guardar_configuracion(config)
                st.success(f"Renta para {sucursal_config} actualizada a ${renta_config:.2f}")
            else:
                st.error("Ingrese el nombre de la sucursal.")

        st.divider()
        st.subheader("🤖 Telegram API")
        bot_token_env = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id_env = os.getenv("TELEGRAM_CHAT_ID", "")
        
        telegram_token = st.text_input("Bot Token", value=bot_token_env, type="password")
        telegram_chat_id = st.text_input("Chat ID", value=chat_id_env)

    # --- DATOS GENERALES ---
    st.header("1. Información del Corte")
    col1, col2 = st.columns(2)

    opciones_sucursales = list(config.keys()) if config else ["GENERAL"]
    with col1:
        sucursal_sel = st.selectbox("Sucursal", opciones=opciones_sucursales + ["OTRA"])
        if sucursal_sel == "OTRA":
            sucursal = st.text_input("Especifique el nombre de la Sucursal").upper().strip()
            renta_defecto = 0.0
        else:
            sucursal = sucursal_sel
            renta_defecto = config.get(sucursal, 0.0)

    with col2:
        usuario = st.text_input("Nombre del Cajero / Usuario").strip().upper()

    # --- CONTADOR DE BILLETES ---
    st.header("2. Desglose de Billetes")
    col_b1, col_b2 = st.columns(2)
    
    cantidades_billetes = {}
    total_billetes = 0.0

    with col_b1:
        for denom in DENOMINACIONES[:3]: # 500, 200, 100
            cantidades_billetes[denom] = st.number_input(
                f"Billetes de ${denom}", min_value=0, value=0, step=1
            )
            total_billetes += cantidades_billetes[denom] * denom

    with col_b2:
        for denom in DENOMINACIONES[3:]: # 50, 20
            cantidades_billetes[denom] = st.number_input(
                f"Billetes de ${denom}", min_value=0, value=0, step=1
            )
            total_billetes += cantidades_billetes[denom] * denom

    st.info(f"**Total Contado en Billetes:** `${total_billetes:,.2f}`")

    # --- VENTAS Y GASTOS ---
    st.header("3. Ventas y Gastos")
    col_v1, col_v2 = st.columns(2)

    with col_v1:
        sistema = st.number_input("Venta reportada por SISTEMA ($)", min_value=0.0, step=10.0)
        terminal = st.number_input("Venta por TERMINAL / TPV ($)", min_value=0.0, step=10.0)
        monedas = st.number_input("Total en MONEDAS (se quedan en tienda) ($)", min_value=0.0, step=1.0)

    with col_v2:
        trabajadora = st.number_input("Sueldo TRABAJADOR(A) ($)", min_value=0.0, step=10.0)
        renta = st.number_input("Renta ($)", min_value=0.0, value=renta_defecto, step=50.0)
        comidas = st.number_input("Gastos de COMIDAS ($)", min_value=0.0, step=5.0)
        otros_gastos = st.number_input("OTROS GASTOS ($)", min_value=0.0, step=5.0)

    # --- CÁLCULO DE RESULTADOS ---
    ahora = datetime.now()
    timestamp = ahora.strftime("%Y-%m-%d_%H-%M-%S")
    fecha_impresion = ahora.strftime("%Y-%m-%d %H:%M:%S")

    datos = {
        "sucursal": sucursal or "GENERAL",
        "usuario": usuario or "N/A",
        "renta": renta,
        "total_billetes": total_billetes,
        "monedas": monedas,
        "sistema": sistema,
        "terminal": terminal,
        "trabajadora": trabajadora,
        "comidas": comidas,
        "otros_gastos": otros_gastos,
        "efectivo": 0.0,
        "subtotal": 0.0,
        "total": 0.0,
        "fecha_impresion": fecha_impresion
    }

    calcular_totales(datos)

    st.divider()
    st.header("📊 RESUMEN DEL CORTE")

    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("Efectivo Recontado", f"${datos['efectivo']:,.2f}")
    m_col2.metric("Subtotal", f"${datos['subtotal']:,.2f}")
    m_col3.metric("TOTAL A ENTREGAR AL DUEÑO", f"${datos['total']:,.2f}")

    # Auditoría de cuadraje
    diferencia = datos['efectivo'] - datos['sistema']
    if abs(diferencia) < 0.01:
        st.success("✅ CAJA CUADRADA PERFECTAMENTE ($0.00)")
    elif diferencia > 0:
        st.warning(f"⚠ SOBRANTE EN CAJA: +${diferencia:,.2f}")
    else:
        st.error(f"❌ FALTANTE EN CAJA: -${abs(diferencia):,.2f}")

    # --- ACCIONES Y DESCARGAS ---
    st.header("4. Generación y Envío de Reportes")
    btn_col1, btn_col2 = st.columns(2)

    # Generación TXT
    txt_bytes = generar_txt_bytes(datos)
    btn_col1.download_button(
        label="📄 Descargar Recibo TXT",
        data=txt_bytes,
        file_name=f"Corte_{datos['sucursal']}_{timestamp}.txt",
        mime="text/plain"
    )

    # Generación PDF
    if REPORTLAB_AVAILABLE:
        pdf_path = f"Corte_{datos['sucursal']}_{timestamp}.pdf"
        generar_pdf(datos, pdf_path)
        
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        btn_col2.download_button(
            label="📕 Descargar Reporte PDF",
            data=pdf_bytes,
            file_name=pdf_path,
            mime="application/pdf"
        )

        st.subheader("🚀 Envío Automático")
        if st.button("Enviar PDF por Telegram"):
            with st.spinner("Enviando reporte a Telegram..."):
                exito, mensaje = enviar_por_telegram(pdf_path, datos, telegram_token, telegram_chat_id)
                if exito:
                    st.success(mensaje)
                else:
                    st.error(mensaje)
    else:
        st.warning("⚠ Instale 'reportlab' para habilitar las opciones de PDF y envío.")

if __name__ == "__main__":
    main()