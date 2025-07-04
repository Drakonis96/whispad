import plotly.graph_objects as go
import plotly.io as pio

# Create figure
fig = go.Figure()

# Define layer positions and correct colors (UI=blue, APIs=green, Storage=orange)
layers = {
    "UI": {"y": 0.8, "color": "#2196F3", "name": "Interfaz Usuario"},
    "Processing": {"y": 0.6, "color": "#4CAF50", "name": "Procesamiento"},
    "APIs": {"y": 0.4, "color": "#4CAF50", "name": "APIs Simuladas"},
    "Storage": {"y": 0.2, "color": "#FF9800", "name": "Almacenamiento"}
}

# Define components for each layer with full names
components = {
    "UI": ["Lista Notas", "Editor Texto", "Panel Transcr", "Herram IA"],
    "Processing": ["Speech-to-Text", "Motor IA", "Gestor Notas", "Validación"],
    "APIs": ["Web Speech", "OpenAI", "Text Enhance", "Voice Record"],
    "Storage": ["LocalStorage", "IndexedDB", "Cache API", "Session"]
}

# Add layer backgrounds
for layer_name, layer_info in layers.items():
    fig.add_shape(
        type="rect",
        x0=0, x1=1,
        y0=layer_info["y"]-0.08, y1=layer_info["y"]+0.08,
        fillcolor=layer_info["color"],
        opacity=0.2,
        line_width=0
    )

# Add layer labels on left
for layer_name, layer_info in layers.items():
    fig.add_annotation(
        x=-0.05, y=layer_info["y"],
        text=layer_info["name"],
        showarrow=False,
        font=dict(size=11, color=layer_info["color"]),
        xanchor="right"
    )

# Add component boxes
box_width = 0.18
x_positions = [0.125, 0.325, 0.525, 0.725]

for layer_name, comps in components.items():
    y_pos = layers[layer_name]["y"]
    color = layers[layer_name]["color"]
    
    for i, comp in enumerate(comps):
        x_pos = x_positions[i]
        
        # Add component box
        fig.add_shape(
            type="rect",
            x0=x_pos-box_width/2, x1=x_pos+box_width/2,
            y0=y_pos-0.04, y1=y_pos+0.04,
            fillcolor=color,
            opacity=0.8,
            line=dict(color="white", width=2)
        )
        
        # Add component text
        fig.add_annotation(
            x=x_pos, y=y_pos,
            text=comp,
            showarrow=False,
            font=dict(size=9, color="white"),
            xanchor="center"
        )

# Add vertical arrows showing data flow between layers
arrow_positions = [0.125, 0.325, 0.525, 0.725]
arrow_labels = ["Audio Input", "Text Process", "AI Enhance", "Voice Record"]

for i, x_pos in enumerate(arrow_positions):
    # UI to Processing
    fig.add_annotation(
        x=x_pos, y=0.6+0.04,
        ax=x_pos, ay=0.8-0.04,
        arrowhead=2,
        arrowsize=1.5,
        arrowwidth=2,
        arrowcolor="#333",
        showarrow=True
    )
    
    # Processing to APIs
    fig.add_annotation(
        x=x_pos, y=0.4+0.04,
        ax=x_pos, ay=0.6-0.04,
        arrowhead=2,
        arrowsize=1.5,
        arrowwidth=2,
        arrowcolor="#333",
        showarrow=True
    )
    
    # APIs to Storage
    fig.add_annotation(
        x=x_pos, y=0.2+0.04,
        ax=x_pos, ay=0.4-0.04,
        arrowhead=2,
        arrowsize=1.5,
        arrowwidth=2,
        arrowcolor="#333",
        showarrow=True
    )

# Add horizontal flow arrows showing data circulation
horizontal_flows = [
    {"from": (0.125, 0.8), "to": (0.325, 0.8), "color": "#2196F3"},
    {"from": (0.325, 0.6), "to": (0.525, 0.6), "color": "#4CAF50"},
    {"from": (0.525, 0.4), "to": (0.725, 0.4), "color": "#4CAF50"},
    {"from": (0.725, 0.2), "to": (0.125, 0.2), "color": "#FF9800"}
]

for flow in horizontal_flows:
    x0, y0 = flow["from"]
    x1, y1 = flow["to"]
    
    fig.add_annotation(
        x=x1, y=y1,
        ax=x0, ay=y0,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=1.5,
        arrowcolor=flow["color"],
        showarrow=True
    )

# Add main process flow descriptions
process_flows = [
    {"x": 0.85, "y": 0.75, "text": "Audio → Speech", "color": "#2196F3"},
    {"x": 0.85, "y": 0.65, "text": "Speech → Text", "color": "#4CAF50"},
    {"x": 0.85, "y": 0.55, "text": "Text → AI", "color": "#4CAF50"},
    {"x": 0.85, "y": 0.45, "text": "AI → Enhanced", "color": "#4CAF50"},
    {"x": 0.85, "y": 0.35, "text": "Data → Storage", "color": "#FF9800"},
    {"x": 0.85, "y": 0.25, "text": "Storage → UI", "color": "#FF9800"}
]

for flow in process_flows:
    fig.add_annotation(
        x=flow["x"], y=flow["y"],
        text=flow["text"],
        showarrow=False,
        font=dict(size=9, color=flow["color"]),
        bordercolor=flow["color"],
        borderwidth=1,
        bgcolor="white",
        borderpad=2
    )

# Update layout
fig.update_layout(
    title="Arquitectura App Notas con IA",
    showlegend=False,
    xaxis=dict(range=[-0.1, 1], showgrid=False, showticklabels=False),
    yaxis=dict(range=[0.1, 0.9], showgrid=False, showticklabels=False),
    plot_bgcolor="white",
    font_size=12
)

# Hide axes
fig.update_xaxes(visible=False)
fig.update_yaxes(visible=False)

fig.write_image("architecture_flowchart.png")