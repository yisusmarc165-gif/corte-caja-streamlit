import streamlit as st
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Corte de Caja Diario",
    page_icon="💵",
    layout="centered"
)

st.title("💵 Sistema de Corte de Caja Diario")
st.markdown("---")

# 1. Datos Generales de la Sucursal
st.header("1. Datos Generales")
col_suc, col_resp = st.columns(2)

with col_suc:
    sucursal = st.text_input("Nombre o ID de la Sucursal", placeholder="Ej. Sucursal Centro")

with col_resp:
    responsable = st.text_input("Responsable del Corte", placeholder="Ej. Juan Pérez")

fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.caption(f"📅 Fecha y Hora de registro: **{fecha_actual}**")

st.markdown("---")

# 2. Desglose de Dinero en Efectivo
st.header("2. Conteo de Denominaciones")

denominaciones_billetes = [1000, 500, 200, 100, 50, 20]
denominaciones_monedas = [20, 10, 5, 2, 1, 0.50]

cantidades = {}

col_billetes, col_monedas = st.columns(2)

with col_billetes:
    st.subheader("💵 Billetes")
    for billete in denominaciones_billetes:
        cantidades[f"billete_{billete}"] = st.number_input(
            f"Billetes de ${billete}:",
            min_value=0,
            step=1,
            value=0,
            key=f"b_{billete}"
        )

with col_monedas:
    st.subheader("🪙 Monedas")
    for moneda in denominaciones_monedas:
        label = f"Monedas de ${moneda:.2f}:" if moneda < 1 else f"Monedas de ${int(moneda)}:"
        cantidades[f"moneda_{moneda}"] = st.number_input(
            label,
            min_value=0,
            step=1,
            value=0,
            key=f"m_{moneda}"
        )

# Cálculos de totales
total_billetes = sum(cantidades[f"billete_{b}"] * b for b in denominaciones_billetes)
total_monedas = sum(cantidades[f"moneda_{m}"] * m for m in denominaciones_monedas)
total_efectivo = total_billetes + total_monedas

st.markdown("---")

# 3. Otros Ingresos / Salidas (Opcional)
st.header("3. Pagos con Tarjeta y Gastos")
col_tarj, col_gastos = st.columns(2)

with col_tarj:
    total_tarjeta = st.number_input("Total cobrado en Tarjeta ($):", min_value=0.0, step=10.0, value=0.0)

with col_gastos:
    gastos_caja = st.number_input("Retiros / Gastos de Caja ($):", min_value=0.0, step=10.0, value=0.0)

gran_total = total_efectivo + total_tarjeta - gastos_caja

# Resumen Financiero
st.markdown("---")
st.header("📊 Resumen del Corte")

res_col1, res_col2, res_col3 = st.columns(3)
res_col1.metric("Efectivo Contado", f"${total_efectivo:,.2f}")
res_col2.metric("Cobros Tarjeta", f"${total_tarjeta:,.2f}")
res_col3.metric("Total Neto en Caja", f"${gran_total:,.2f}", delta=f"-${gastos_caja:,.2f} Gastos" if gastos_caja > 0 else None)

# Generación del Reporte en Texto (.txt)
def generar_reporte_txt():
    lineas = [
        "==================================================",
        "          REPORTE DE CORTE DE CAJA DIARIO         ",
        "==================================================",
        f"Fecha y Hora : {fecha_actual}",
        f"Sucursal     : {sucursal if sucursal else 'N/A'}",
        f"Responsable  : {responsable if responsable else 'N/A'}",
        "--------------------------------------------------",
        "DESGLOSE DE BILLETES:",
    ]
    for b in denominaciones_billetes:
        cnt = cantidades[f"billete_{b}"]
        if cnt > 0:
            lineas.append(f"  - ${b:4d} x {cnt:3d} = ${b * cnt:10.2f}")
    
    lineas.append("\nDESGLOSE DE MONEDAS:")
    for m in denominaciones_monedas:
        cnt = cantidades[f"moneda_{m}"]
        if cnt > 0:
            lineas.append(f"  - ${m:5.2f} x {cnt:3d} = ${m * cnt:10.2f}")
            
    lineas.extend([
        "--------------------------------------------------",
        f"Total Billetes  : ${total_billetes:12.2f}",
        f"Total Monedas   : ${total_monedas:12.2f}",
        f"TOTAL EFECTIVO  : ${total_efectivo:12.2f}",
        f"Total Tarjeta   : ${total_tarjeta:12.2f}",
        f"Gastos / Retiros: ${gastos_caja:12.2f}",
        "--------------------------------------------------",
        f"GRAN TOTAL CAJA : ${gran_total:12.2f}",
        "==================================================",
    ])
    return "\n".join(lineas)

st.markdown("---")

# Botón para descargar el reporte
reporte_texto = generar_reporte_txt()

st.download_button(
    label="📄 Descargar Reporte (.txt)",
    data=reporte_texto,
    file_name=f"corte_{sucursal.replace(' ', '_') if sucursal else 'caja'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
    mime="text/plain",
    type="primary"
)