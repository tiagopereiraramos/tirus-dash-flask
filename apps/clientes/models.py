class Cliente(db.Model):
    # ...existing code...
    @staticmethod
    def listar_ativos():
        return db.session.query(Cliente)\
            .join(Operadora)\
            .filter(Cliente.status_ativo == True, Operadora.status_ativo == True)\
            .order_by(Cliente.razao_social)\
            .all()
    # ...existing code...
