import pandas as pd
import plotly.graph_objects as go

# Data provided
funcionalidades = [
    {"nombre": "Transcripción de Audio", "implementacion": 95},
    {"nombre": "Mejora de Texto con IA", "implementacion": 90},
    {"nombre": "Gestión de Notas", "implementacion": 100},
    {"nombre": "Búsqueda y Filtrado", "implementacion": 85},
    {"nombre": "Almacenamiento Local", "implementacion": 95},
    {"nombre": "Interfaz Responsive", "implementacion": 90},
    {"nombre": "Editor de Texto Rico", "implementacion": 88},
    {"nombre": "Simulación de APIs", "implementacion": 92}
]

# Create DataFrame
df = pd.DataFrame(funcionalidades)

# Map long names to <=15 char labels
label_map = {
    "Transcripción de Audio": "Transc Audio",
    "Mejora de Texto con IA": "Mejora IA",
    "Gestión de Notas": "Gest Notas",
    "Búsqueda y Filtrado": "Busqueda",
    "Almacenamiento Local": "Almac Local",
    "Interfaz Responsive": "UI Responsive",
    "Editor de Texto Rico": "Edit Txt Rico",
    "Simulación de APIs": "Simul APIs"
}

df["label"] = df["nombre"].map(label_map)

# Brand colors in required order
colors = [
    "#1FB8CD", "#FFC185", "#ECEBD5", "#5D878F",
    "#D2BA4C", "#B4413C", "#964325", "#944454"
]

# Horizontal bar chart
fig = go.Figure(
    go.Bar(
        x=df["implementacion"],
        y=df["label"],
        orientation="h",
        marker_color=colors,
        showlegend=False,
        cliponaxis=False
    )
)

# Title and axes
fig.update_layout(title_text="Nivel de funciones clave")
fig.update_xaxes(title_text="Nivel (%)", range=[0, 100])
fig.update_yaxes(title_text="Función")

# Save figure
fig.write_image("functionality_bar.png")