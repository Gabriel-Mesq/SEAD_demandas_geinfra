from .tecnico_routes import tecnico_bp
# from .outra_rota import outra_bp  # Se você tiver outros Blueprints

# Lista de Blueprints que serão registrados no app principal
blueprints = [
    tecnico_bp,
    # outra_bp,  # Descomente se tiver mais Blueprints
]

def register_blueprints(app):
    for bp in blueprints:
        app.register_blueprint(bp)
