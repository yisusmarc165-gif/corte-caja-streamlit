# -*- coding: utf-8 -*-
"""
SISTEMA DE CORTE DE CAJA DIARIO (CON GENERACIÓN DE TXT, PDF Y ENVÍO AUTOMÁTICO)
=======================================================================================
Autor: Asistente Python
Descripción:
    Este script realiza la captura, cálculo y auditoría de corte de caja diario.
    Genera automáticamente el comprobante en TXT y en PDF profesional.
    Permite enviar el PDF generado a un número telefónico o grupo en Telegram/WhatsApp 
    sin costo utilizando la API Bot de Telegram.

Requisitos previos:
    pip install reportlab requests
"""

import json
import os
import sys
from datetime import datetime
import requests

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

# ==========================================
# CONFIGURACIÓN DE NOTIFICACIONES (TELEGRAM / WHATSAPP)
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")  # Ej: "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")      # Ej: "987654321" o "-100123456789"

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

def obtener_o_configurar_renta(sucursal, config):
    if sucursal not in config:
        print(f"\n[CONFIGURACIÓN NUEVA] La sucursal '{sucursal}' no tiene renta registrada.")
        while True:
            try:
                renta = float(input(f"Ingrese la RENTA fija para '{sucursal}': $"))
                config[sucursal] = renta
                guardar_configuracion(config)
                print(f"✓ Renta de ${renta:.2f} guardada.\n")
                break
            except ValueError:
                print("❌ Ingrese un monto numérico válido.")
    return config[sucursal]

def capturar_billetes():
    print("\n--- CALCULADORA DE BILLETES ---")
    total_billetes = 0
    for denom in DENOMINACIONES:
        while True:
            try:
                cant = input(f"Cantidad de billetes de ${denom}: ").strip()
                cant = int(cant) if cant != "" else 0
                if cant < 0:
                    print("❌ No puede ingresar cantidades negativas.")
                    continue
                total_billetes += cant * denom
                break
            except ValueError:
                print("❌ Ingrese un número entero válido.")
    
    print("\n" + "-" * 35)
    print(f" TOTAL EN BILLETES CONTADOS: ${total_billetes:.2f}")
    print("-" * 35 + "\n")
    return total_billetes

def calcular_totales(datos):
    # 1. EFECTIVO = Billetes + Terminal + Comidas + Otros Gastos + Monedas
    datos['efectivo'] = (datos['total_billetes'] + datos['terminal'] + 
                        datos['comidas'] + datos['otros_gastos'] + datos['monedas'])
    
    # 2. SUBTOTAL = Efectivo - Trabajadora - Renta - Comidas - Otros Gastos
    datos['subtotal'] = (datos['efectivo'] - datos['trabajadora'] - 
                         datos['renta'] - datos['comidas'] - datos['otros_gastos'])
    
    # 3. TOTAL A ENTREGAR AL DUEÑO (Billetes - Trabajadora - Renta)
    datos['total'] = datos['total_billetes'] - datos['trabajadora'] - datos['renta']

def imprimir_tabla_corte(datos):
    print("\n" + "=" * 45)
    print(f"            CORTE DE CAJA - {datos['sucursal']}")
    print("=" * 45)
    print(f"  USUARIO:        {datos['usuario']}")
    print(f"  SISTEMA:        ${datos['sistema']:10.2f}")
    print(f"  EFECTIVO:       ${datos['efectivo']:10.2f}")
    print(f"  TERMINAL:       ${datos['terminal']:10.2f}")
    print(f"  TRABAJADOR(A):  ${datos['trabajadora']:10.2f}")
    print(f"  RENTA:          ${datos['renta']:10.2f}")
    print(f"  COMIDAS:        ${datos['comidas']:10.2f}")
    print(f"  OTROS GASTOS:   ${datos['otros_gastos']:10.2f}")
    print(f"  MONEDAS:        ${datos['monedas']:10.2f}")
    print("  -------------------------------------------")
    print(f"  subtotal:       ${datos['subtotal']:10.2f}")
    print("  ===========================================")
    print(f"  TOTAL:          ${datos['total']:10.2f}")
    print("=" * 45)
    
    diferencia = datos['efectivo'] - datos['sistema']
    if abs(diferencia) < 0.01:
        print("  ✓ CAJA CUADRADA PERFECTAMENTE (Diferencia: $0.00)")
    elif diferencia > 0:
        print(f"  ⚠ SOBRANTE EN CAJA: +${diferencia:.2f}")
    else:
        print(f"  ❌ FALTANTE EN CAJA: -${abs(diferencia):.2f}")
    print("=" * 45)

def guardar_en_archivo_txt(datos, timestamp):
    """Genera y guarda un archivo .txt individual con el recibo del corte."""
    nombre_archivo = f"Corte_{datos['sucursal']}_{timestamp}.txt"
    
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

    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(contenido)
        
    print(f"✓ Archivo TXT generado: {nombre_archivo}")
    return nombre_archivo

def generar_pdf(datos, timestamp):
    """Genera un reporte PDF con diseño limpio y profesional."""
    nombre_pdf = f"Corte_{datos['sucursal']}_{timestamp}.pdf"
    
    if not REPORTLAB_AVAILABLE:
        print("⚠ Advertencia: ReportLab no está instalado. Instálelo con 'pip install reportlab' para generar PDFs.")
        return None

    doc = SimpleDocTemplate(
        nombre_pdf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E293B'),
        alignment=0
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B')
    )
    
    cell_style = ParagraphStyle(
        'Cell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#334155')
    )

    cell_style_bold = ParagraphStyle(
        'CellBold',
        parent=cell_style,
        fontName='Helvetica-Bold'
    )

    diferencia = datos['efectivo'] - datos['sistema']
    if abs(diferencia) < 0.01:
        estado_txt = "CAJA CUADRADA PERFECTAMENTE ($0.00)"
        color_estado = colors.HexColor('#166534') # Verde
        bg_estado = colors.HexColor('#DCFCE7')
    elif diferencia > 0:
        estado_txt = f"SOBRANTE EN CAJA: +${diferencia:.2f}"
        color_estado = colors.HexColor('#9A3412') # Naranja
        bg_estado = colors.HexColor('#FFEDD5')
    else:
        estado_txt = f"FALTANTE EN CAJA: -${abs(diferencia):.2f}"
        color_estado = colors.HexColor('#991B1B') # Rojo
        bg_estado = colors.HexColor('#FEE2E2')

    story = []

    # Encabezado
    story.append(Paragraph(f"CORTE DE CAJA - {datos['sucursal']}", title_style))
    story.append(Paragraph(f"Fecha de Emisión: {datos['fecha_impresion']} | Atendido por: {datos['usuario']}", subtitle_style))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#CBD5E1'), spaceAfter=15))

    # Tabla principal
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

    # Cuadro de Estado / Balance
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
    print(f"✓ Archivo PDF generado: {nombre_pdf}")
    return nombre_pdf

def enviar_por_telegram(pdf_path, datos, token=None, chat_id=None):
    """Envía el archivo PDF adjunto y un resumen por Telegram usando Bot API."""
    token = token or TELEGRAM_BOT_TOKEN
    chat_id = chat_id or TELEGRAM_CHAT_ID

    if not token or not chat_id:
        print("\n⚠ Para envío por Telegram/WhatsApp sin costo, configure TOKEN y CHAT_ID.")
        token_input = input("Ingrese Bot Token de Telegram (o presione Enter para omitir): ").strip()
        chat_id_input = input("Ingrese Chat ID o Celular Destino (o presione Enter para omitir): ").strip()
        if not token_input or not chat_id_input:
            print("❌ Envío omitido por falta de credenciales.")
            return False
        token, chat_id = token_input, chat_id_input

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
            print(f"🚀 Enviando PDF a Telegram (ID: {chat_id})...")
            response = requests.post(url, data=data, files=files, timeout=15)
            
        if response.status_code == 200:
            print("✅ ¡PDF enviado con éxito por Telegram/WhatsApp sin costo!")
            return True
        else:
            print(f"❌ Error al enviar mensaje ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error de conexión al enviar el reporte: {e}")
        return False

def menu_corregir(datos):
    while True:
        imprimir_tabla_corte(datos)
        print("\n--- MENÚ DE CORRECCIÓN / CONFIRMACIÓN ---")
        print(" 1. Corregir Usuario")
        print(" 2. Corregir Venta por Sistema")
        print(" 3. Recontar Billetes")
        print(" 4. Corregir Terminal")
        print(" 5. Corregir Sueldo Trabajador(a)")
        print(" 6. Corregir Renta")
        print(" 7. Corregir Comidas")
        print(" 8. Corregir Otros Gastos")
        print(" 9. Corregir Monedas")
        print("10. TODO CORRECTO -> Continuar")
        
        opc = input("\nSeleccione una opción (1-10): ").strip()
        
        try:
            if opc == "1":
                datos['usuario'] = input("Nuevo usuario: ").strip().upper()
            elif opc == "2":
                datos['sistema'] = float(input("Nuevo valor Sistema: $"))
            elif opc == "3":
                datos['total_billetes'] = capturar_billetes()
            elif opc == "4":
                datos['terminal'] = float(input("Nuevo valor Terminal: $"))
            elif opc == "5":
                datos['trabajadora'] = float(input("Nuevo Sueldo Trabajador(a): $"))
            elif opc == "6":
                datos['renta'] = float(input("Nuevo valor Renta: $"))
            elif opc == "7":
                datos['comidas'] = float(input("Nuevo valor Comidas: $"))
            elif opc == "8":
                datos['otros_gastos'] = float(input("Nuevo valor Otros Gastos: $"))
            elif opc == "9":
                datos['monedas'] = float(input("Nuevo valor Monedas: $"))
            elif opc == "10":
                break
            else:
                print("❌ Opción inválida.")
                continue
            
            calcular_totales(datos)
        except ValueError:
            print("❌ Entrada inválida. Debe ingresar un número.")

def realizar_corte():
    while True:
        config = cargar_configuracion()
        
        print("\n" + "=" * 50)
        print("        SISTEMA DE CORTE DE CAJA DIARIO")
        print("=" * 50)
        
        sucursal = input("Nombre o ID de la Sucursal: ").strip().upper() or "GENERAL"
        usuario = input("Nombre del cajero/usuario: ").strip().upper()
        
        renta = obtener_o_configurar_renta(sucursal, config)
        total_billetes = capturar_billetes()
        
        while True:
            try:
                monedas = float(input("Total en MONEDAS (se quedan en tienda): $") or 0)
                break
            except ValueError:
                print("❌ Ingrese un monto numérico.")

        print("\n--- DATOS DE SISTEMA Y GASTOS ---")
        while True:
            try:
                sistema = float(input("Venta reportada por SISTEMA: $") or 0)
                terminal = float(input("Venta por TERMINAL (TPV): $") or 0)
                trabajadora = float(input("Sueldo de TRABAJADOR(A): $") or 0)
                comidas = float(input("Gastos de COMIDAS: $") or 0)
                otros_gastos = float(input("OTROS GASTOS: $") or 0)
                break
            except ValueError:
                print("❌ Por favor ingrese valores numéricos válidos.")

        ahora = datetime.now()
        timestamp = ahora.strftime("%Y-%m-%d_%H-%M-%S")
        fecha_impresion = ahora.strftime("%Y-%m-%d %H:%M:%S")

        datos = {
            "sucursal": sucursal,
            "usuario": usuario,
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
        menu_corregir(datos)
        
        print("\n--- OPCIONES FINALES ---")
        print("1. Guardar corte (Generar TXT + PDF, Enviar y Salir)")
        print("2. Reiniciar un NUEVO corte desde el inicio")
        print("3. Salir sin guardar")
        
        fin = input("\nSeleccione una opción (1-3): ").strip()
        if fin == "1":
            txt_path = guardar_en_archivo_txt(datos, timestamp)
            pdf_path = generar_pdf(datos, timestamp)
            
            if pdf_path and os.path.exists(pdf_path):
                enviar_opt = input("\n¿Desea enviar el reporte PDF por Telegram / WhatsApp ahora? (s/n): ").strip().lower()
                if enviar_opt in ['s', 'si', 'y', 'yes']:
                    enviar_por_telegram(pdf_path, datos)

            print("\n¡Corte finalizado y guardado con éxito! Hasta luego.")
            break
        elif fin == "2":
            print("\nReiniciando proceso...")
            continue
        else:
            print("\nSaliendo del programa.")
            break

if __name__ == "__main__":
    realizar_corte()