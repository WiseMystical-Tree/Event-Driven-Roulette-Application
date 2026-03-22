""" 
Como esta roleta é para a Lusíada Games Week, faz sentido haver um campo para introduzir
o email de cada pessoa. Assim, cada participante teria apenas uma jogada de 30 em 30 minutos.
O email serviria para saber para onde enviar o prémio. Desta forma, também seria mais fácil
ajustar as probabilidades dos prémios em tempo real. Poderíamos ainda fazer um reset ao sistema
de probabilidades a cada 20 jogadas, por exemplo.
O ficheiro Email_Roleta.txt tem as informações do que se tem de trocar, adicionar etc no código principal
"""

import sqlite3
import tkinter as tk
import random
import math

# =========================================================
# CONFIGURAÇÕES GERAIS DO PROGRAMA
# =========================================================
NOME_BD = "Projeto_Roleta.db"

PREMIOS_INICIAIS = [
    {"nome": "100€", "cor": "#FF5733", "peso_base": 2,  "peso_min": 0.8,   "peso_max": 3},
    {"nome": "50€", "cor": "#33FF57", "peso_base": 2,   "peso_min": 0.8,   "peso_max": 3},
    {"nome": "Jackpot", "cor": "#3357FF", "peso_base": 1,  "peso_min": 0.2, "peso_max": 2},
    {"nome": "Tente novamente", "cor": "#FF33A1", "peso_base": 12, "peso_min": 5,   "peso_max": 14},
    {"nome": "20€", "cor": "#A133FF", "peso_base": 10, "peso_min": 3,   "peso_max": 12},
    {"nome": "10€", "cor": "#33FFF5", "peso_base": 25, "peso_min": 20,   "peso_max": 30},
    {"nome": "500€", "cor": "#F5FF33", "peso_base": 3, "peso_min": 1,   "peso_max": 5},
    {"nome": "Sem Prémio", "cor": "#FF8C33", "peso_base": 45, "peso_min": 40, "peso_max": 60},
]


# =========================================================
# FUNÇÕES RELACIONADAS COM A BASE DE DADOS
# =========================================================
def ligar_bd():
    conn = sqlite3.connect(NOME_BD)
    conn.row_factory = sqlite3.Row
    return conn


def criar_tabelas():
    conn = ligar_bd()
    cursor = conn.cursor()

    # Esta tabela guarda os prémios existentes na roleta
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS premios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            cor TEXT NOT NULL,
            stock_atual INTEGER,
            stock_inicial INTEGER,
            peso_base REAL NOT NULL,
            peso_atual REAL NOT NULL,
            peso_min REAL NOT NULL,
            peso_max REAL NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1
        )
    """)

    # Aqui fica registado o histórico de todas as jogadas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jogadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_premio INTEGER NOT NULL,
            premio_nome TEXT NOT NULL,
            peso_usado REAL NOT NULL,
            data_jogada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_premio) REFERENCES premios(id)
        )
    """)

    # Esta tabela guarda o histórico das alterações feitas aos pesos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_pesos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_premio INTEGER NOT NULL,
            peso_anterior REAL NOT NULL,
            peso_novo REAL NOT NULL,
            motivo TEXT,
            registado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_premio) REFERENCES premios(id)
        )
    """)

    conn.commit()
    conn.close()


def inserir_premios_iniciais():
    conn = ligar_bd()
    cursor = conn.cursor()

    # Insere os prémios iniciais apenas se ainda não existirem
    for premio in PREMIOS_INICIAIS:
        cursor.execute("""
            INSERT OR IGNORE INTO premios
            (nome, cor, stock_atual, stock_inicial, peso_base, peso_atual, peso_min, peso_max, ativo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            premio["nome"],
            premio["cor"],
            None,
            None,
            premio["peso_base"],
            premio["peso_base"],
            premio["peso_min"],
            premio["peso_max"]
        ))

    conn.commit()
    conn.close()


def obter_premios_ativos():
    conn = ligar_bd()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT *
        FROM premios
        WHERE ativo = 1
        ORDER BY id
    """)
    premios = cursor.fetchall()
    conn.close()
    return premios


def registar_jogada(id_premio, nome_premio, peso_usado):
    conn = ligar_bd()
    cursor = conn.cursor()

    # Guarda uma nova jogada no histórico
    cursor.execute("""
        INSERT INTO jogadas (id_premio, premio_nome, peso_usado)
        VALUES (?, ?, ?)
    """, (id_premio, nome_premio, peso_usado))

    conn.commit()
    conn.close()


def contar_total_jogadas():
    conn = ligar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM jogadas")
    total = cursor.fetchone()["total"]
    conn.close()
    return total


def contar_saidas_premio(id_premio):
    conn = ligar_bd()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM jogadas
        WHERE id_premio = ?
    """, (id_premio,))
    total = cursor.fetchone()["total"]
    conn.close()
    return total


def atualizar_peso_premio(id_premio, peso_novo, motivo):
    conn = ligar_bd()
    cursor = conn.cursor()

    cursor.execute("SELECT peso_atual FROM premios WHERE id = ?", (id_premio,))
    linha = cursor.fetchone()

    # Se o prémio não existir, sai da função sem fazer nada
    if linha is None:
        conn.close()
        return

    peso_anterior = linha["peso_atual"]

    # Atualiza o peso atual do prémio
    cursor.execute("""
        UPDATE premios
        SET peso_atual = ?
        WHERE id = ?
    """, (peso_novo, id_premio))

    # Guarda também essa alteração no histórico
    cursor.execute("""
        INSERT INTO historico_pesos (id_premio, peso_anterior, peso_novo, motivo)
        VALUES (?, ?, ?, ?)
    """, (id_premio, peso_anterior, peso_novo, motivo))

    conn.commit()
    conn.close()


def recalcular_pesos():
    """
    Esta função ajusta os pesos dos prémios com base no histórico das jogadas.

    Ideia geral:
    - conta quantas vezes cada prémio já saiu;
    - compara esse valor com aquilo que seria esperado segundo o peso base;
    - se um prémio saiu mais vezes do que o esperado, o seu peso baixa um pouco;
    - se saiu menos vezes do que o esperado, o seu peso sobe um pouco;
    - o valor final nunca pode passar dos limites mínimo e máximo definidos.
    """
    premios = obter_premios_ativos()
    total_jogadas = contar_total_jogadas()

    if not premios:
        return

    soma_pesos_base = sum(float(p["peso_base"]) for p in premios)

    # Se ainda não houver jogadas, cada prémio volta ao seu peso base
    if total_jogadas == 0:
        for premio in premios:
            atualizar_peso_premio(
                premio["id"],
                float(premio["peso_base"]),
                "Reposição para o peso base por não existir histórico de jogadas"
            )
        return

    for premio in premios:
        peso_base = float(premio["peso_base"])
        peso_min = float(premio["peso_min"])
        peso_max = float(premio["peso_max"])
        saidas_reais = contar_saidas_premio(premio["id"])

        # Calcula quantas vezes este prémio deveria ter saído,
        # tendo em conta o total de jogadas e o seu peso base
        saidas_esperadas = total_jogadas * (peso_base / soma_pesos_base)

        # Mede a diferença entre o que realmente saiu e o que seria esperado
        # Valor positivo: saiu mais vezes do que devia
        # Valor negativo: saiu menos vezes do que devia
        diferenca = saidas_reais - saidas_esperadas

        # Evita ajustes demasiado agressivos em prémios raros
        if saidas_esperadas < 1:
            saidas_esperadas = 1

        desvio_relativo = diferenca / saidas_esperadas

        # Fator de correção moderado
        fator = 1 - (0.25 * desvio_relativo)

        # Limita a força do ajuste para evitar alterações bruscas
        if fator < 0.70:
            fator = 0.70
        elif fator > 1.30:
            fator = 1.30

        peso_novo = peso_base * fator

        # Garante que o novo peso fica sempre dentro dos limites definidos
        if peso_novo < peso_min:
            peso_novo = peso_min
        elif peso_novo > peso_max:
            peso_novo = peso_max

        motivo = (
            f"Recalculo automático: reais={saidas_reais}, "
            f"esperadas={saidas_esperadas:.2f}, fator={fator:.4f}"
        )

        atualizar_peso_premio(premio["id"], peso_novo, motivo)


# =========================================================
# CLASSE PRINCIPAL DA ROLETA
# =========================================================
class RolPremios:
    def __init__(self, root):
        self.root = root
        self.root.title("Roleta de Prémios")
        self.root.geometry("520x670")
        self.root.resizable(False, False)

        self.raio_roleta = 190
        self.centro_x = 250
        self.centro_y = 220

        self.angulo_atual = 0
        self.a_girar = False
        self.premios = []

        # Área onde a roleta é desenhada
        self.canvas = tk.Canvas(root, width=500, height=450, bg="white")
        self.canvas.pack(pady=10)

        # Texto onde aparece o prémio final
        self.label_resultado = tk.Label(root, text="", font=("Arial", 16, "bold"))
        self.label_resultado.pack(pady=10)

        # Texto complementar com informação adicional
        self.label_info = tk.Label(
            root,
            text="Pronto para jogar.",
            font=("Arial", 10),
            justify="center"
        )
        self.label_info.pack(pady=5)

        # Botão que inicia a jogada
        self.btn_girar = tk.Button(root, text="Girar!", font=("Arial", 12, "bold"), command=self.iniciar_girar)
        self.btn_girar.pack(pady=15)

        # Seta fixa no topo da roleta, que indica o prémio vencedor
        self.canvas.create_polygon(240, 15, 260, 15, 250, 30, fill="black", tags="seta")

        # Carrega os prémios da base de dados e desenha a roleta
        self.recarregar_premios()
        self.desenhar_roda()

    def recarregar_premios(self):
        self.premios = obter_premios_ativos()
        self.numero_segmentos = len(self.premios)
        self.angulo_segmento = 360 / self.numero_segmentos if self.numero_segmentos > 0 else 360

    def desenhar_roda(self):
        self.canvas.delete("segmento")

        if not self.premios:
            return

        for i, premio in enumerate(self.premios):
            angulo_inicio = self.angulo_atual + (i * self.angulo_segmento)

            self.canvas.create_arc(
                self.centro_x - self.raio_roleta,
                self.centro_y - self.raio_roleta,
                self.centro_x + self.raio_roleta,
                self.centro_y + self.raio_roleta,
                start=angulo_inicio,
                extent=self.angulo_segmento,
                fill=premio["cor"],
                outline="black",
                width=2,
                tags="segmento"
            )

            angulo_meio = angulo_inicio + self.angulo_segmento / 2
            rad = math.radians(angulo_meio)
            x = self.centro_x + 120 * math.cos(rad)
            y = self.centro_y - 120 * math.sin(rad)

            # Escreve o nome do prémio dentro da respetiva fatia
            self.canvas.create_text(
                x,
                y,
                text=premio["nome"],
                font=("Arial", 10, "bold"),
                tags="segmento"
            )

    def escolher_premio_por_peso(self):
        pesos = [float(p["peso_atual"]) for p in self.premios]
        escolhido = random.choices(self.premios, weights=pesos, k=1)[0]
        return escolhido

    def iniciar_girar(self):
        if self.a_girar:
            return

        # Volta a ler os prémios da base de dados e escolhe um
        # com base nos pesos atuais
        self.recarregar_premios()
        premio_escolhido = self.escolher_premio_por_peso()

        self.premio_sorteado = premio_escolhido
        self.indice_premio_sorteado = next(
            i for i, p in enumerate(self.premios) if p["id"] == premio_escolhido["id"]
        )

        # Prepara a animação da roleta para ela terminar exatamente
        # no prémio que foi sorteado
        self.angulo_inicial_animacao = self.angulo_atual
        voltas_extra = random.randint(4, 6)

        # O centro da fatia sorteada tem de ficar alinhado com a seta do topo
        angulo_desejado = 90 - (
            self.indice_premio_sorteado * self.angulo_segmento + self.angulo_segmento / 2
        )

        self.angulo_final_animacao = angulo_desejado + 360 * voltas_extra

        # Se o valor final ficar atrás da posição atual, acrescenta mais voltas
        while self.angulo_final_animacao <= self.angulo_inicial_animacao:
            self.angulo_final_animacao += 360

        self.frame_atual = 0
        self.total_frames = 120

        self.a_girar = True
        self.btn_girar.config(state="disabled")
        self.label_resultado.config(text="")
        self.label_info.config(text="A girar...")

        self.animar_roda()

    def animar_roda(self):
        if self.frame_atual < self.total_frames:
            t = self.frame_atual / self.total_frames

            # Esta fórmula faz com que a roleta abrande de forma suave
            progresso = 1 - pow(1 - t, 3)

            self.angulo_atual = (
                self.angulo_inicial_animacao
                + (self.angulo_final_animacao - self.angulo_inicial_animacao) * progresso
            )

            self.desenhar_roda()
            self.frame_atual += 1
            self.root.after(20, self.animar_roda)
        else:
            self.angulo_atual = self.angulo_final_animacao % 360
            self.desenhar_roda()
            self.finalizar_giro()

    def finalizar_giro(self):
        premio = self.premio_sorteado

        # Guarda a jogada no histórico da base de dados
        registar_jogada(
            id_premio=premio["id"],
            nome_premio=premio["nome"],
            peso_usado=float(premio["peso_atual"])
        )

        # Depois da jogada, os pesos são recalculados com base no histórico atualizado
        recalcular_pesos()

        # Atualiza os prémios depois do recálculo
        self.recarregar_premios()

        self.label_resultado.config(text=f"Prémio: {premio['nome']}")
        self.label_info.config(text="Pode jogar novamente.")

        self.a_girar = False
        self.btn_girar.config(state="normal")


# =========================================================
# ARRANQUE DO PROGRAMA
# =========================================================
if __name__ == "__main__":
    criar_tabelas()
    inserir_premios_iniciais()

    root = tk.Tk()
    app = RolPremios(root)
    root.mainloop()