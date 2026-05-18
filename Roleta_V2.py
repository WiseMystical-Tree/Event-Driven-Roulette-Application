#!/usr/bin/env python3


import sqlite3
import tkinter as tk
from tkinter import simpledialog, messagebox
import random
import math
import re
import csv
from pathlib import Path


# =========================================================
# CONFIGURAÇÕES GERAIS DO PROGRAMA
# =========================================================
NOME_BD = "Projeto_Roleta_teste.db"  # Nome da base de dados
EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"  # Expressão regular para validar email

# O programa procura por premios.csv. Se não existir, não haverá prémios.
FICHEIRO_PREMIOS_CSV = "premios.csv"

# =========================================================
def gerar_cor_aleatoria():
    # Gera uma cor aleatória em formato hexadecimal
    return "#{:06X}".format(random.randint(0, 0xFFFFFF))


def texto_para_float(valor, nome_campo, nome_premio):
    try:
        return float(str(valor).strip().replace(",", "."))
    except Exception:
        raise ValueError(
            f"O campo '{nome_campo}' do prémio '{nome_premio}' não é numérico."
        )


def normalizar_nome_premio(nome):
    return str(nome).strip()

# =========================================================
# LEITURA DE PRÉMIOS A PARTIR DE CSV
# =========================================================
def ler_premios_csv(caminho):
    premios = []

    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        leitor = csv.reader(f)
        rows = []
        for row in leitor:
            if row and not str(row[0]).strip().startswith('#'):
                rows.append(row)

        if not rows:
            raise ValueError("O ficheiro CSV não tem linhas de dados válidas.")

        fieldnames = [c.strip() for c in rows[0]]
        data_rows = rows[1:]

        colunas_necessarias = {"nome", "peso_base", "peso_min", "peso_max"}
        colunas_lidas = {c.lower() for c in fieldnames}

        if not colunas_necessarias.issubset(colunas_lidas):
            raise ValueError(
                "O ficheiro CSV tem de ter pelo menos as colunas: "
                "nome, peso_base, peso_min, peso_max"
            )

        for i, linha in enumerate(data_rows, start=2):
            linha_dict = dict(zip(fieldnames, linha))
            nome = normalizar_nome_premio(linha_dict.get("nome", ""))

            if not nome:
                raise ValueError(f"Linha {i} do CSV sem nome de prémio.")

            peso_base = texto_para_float(linha_dict.get("peso_base", ""), "peso_base", nome)
            peso_min = texto_para_float(linha_dict.get("peso_min", ""), "peso_min", nome)
            peso_max = texto_para_float(linha_dict.get("peso_max", ""), "peso_max", nome)

            cor = str(linha_dict.get("cor", "") or "").strip()
            if not cor:
                cor = gerar_cor_aleatoria()

            if peso_min > peso_base or peso_base > peso_max:
                raise ValueError(
                    f"No prémio '{nome}' os pesos têm de respeitar: "
                    f"peso_min <= peso_base <= peso_max."
                )

            premios.append({
                "nome": nome,
                "cor": cor,
                "peso_base": peso_base,
                "peso_min": peso_min,
                "peso_max": peso_max
            })

    return premios

def carregar_premios_do_ficheiro():
    caminho_csv = Path(FICHEIRO_PREMIOS_CSV)

    if caminho_csv.exists():
        premios = ler_premios_csv(caminho_csv)
        origem = str(caminho_csv)
    else:
        raise FileNotFoundError(
            f"Não foi encontrado o '{FICHEIRO_PREMIOS_CSV}'."
        )

    if not premios:
        raise ValueError(f"O ficheiro '{origem}' não contém prémios válidos.")

    nomes = [p["nome"].strip().lower() for p in premios]
    if len(nomes) != len(set(nomes)):
        raise ValueError("Existem prémios com nome repetido no ficheiro de prémios.")

    return premios, origem


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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            tentativas_disponiveis INTEGER NOT NULL DEFAULT 1,
            total_jogadas INTEGER NOT NULL DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jogadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_participante INTEGER NOT NULL,
            email_snapshot TEXT NOT NULL,
            id_premio INTEGER NOT NULL,
            premio_nome TEXT NOT NULL,
            peso_usado REAL NOT NULL,
            data_jogada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_participante) REFERENCES participantes(id),
            FOREIGN KEY (id_premio) REFERENCES premios(id)
        )
    """)

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


def sincronizar_premios_com_ficheiro():
    """
    O ficheiro de prémios é a fonte de verdade:
    - se um prémio existir no ficheiro e não existir na BD -> adiciona
    - se existir nos dois -> atualiza
    - se existir na BD mas não no ficheiro -> desativa
    """
    premios_ficheiro, origem = carregar_premios_do_ficheiro()

    conn = ligar_bd()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM premios")
    premios_bd = cursor.fetchall()
    premios_bd_por_nome = {linha["nome"].strip().lower(): linha for linha in premios_bd}

    nomes_ficheiro = set()

    for premio in premios_ficheiro:
        nome = premio["nome"]
        chave = nome.strip().lower()
        nomes_ficheiro.add(chave)

        existente = premios_bd_por_nome.get(chave)

        if existente is None:
            cursor.execute("""
                INSERT INTO premios
                (nome, cor, stock_atual, stock_inicial, peso_base, peso_atual, peso_min, peso_max, ativo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                nome,
                premio["cor"],
                None,
                None,
                premio["peso_base"],
                premio["peso_base"],
                premio["peso_min"],
                premio["peso_max"]
            ))
        else:
            peso_atual_antigo = float(existente["peso_atual"])
            peso_base_antigo = float(existente["peso_base"])
            peso_min_antigo = float(existente["peso_min"])
            peso_max_antigo = float(existente["peso_max"])

            # Mantém o peso_atual existente, exceto se ficar fora dos novos limites
            novo_peso_atual = peso_atual_antigo

            if novo_peso_atual < premio["peso_min"]:
                novo_peso_atual = premio["peso_min"]
            if novo_peso_atual > premio["peso_max"]:
                novo_peso_atual = premio["peso_max"]

            if abs(peso_atual_antigo - peso_base_antigo) < 1e-9:
                novo_peso_atual = premio["peso_base"]

            cursor.execute("""
                UPDATE premios
                SET nome = ?,
                    cor = ?,
                    peso_base = ?,
                    peso_atual = ?,
                    peso_min = ?,
                    peso_max = ?,
                    ativo = 1
                WHERE id = ?
            """, (
                nome,
                premio["cor"],
                premio["peso_base"],
                novo_peso_atual,
                premio["peso_min"],
                premio["peso_max"],
                existente["id"]
            ))

            houve_alteracao_pesos = (
                peso_base_antigo != premio["peso_base"]
                or peso_min_antigo != premio["peso_min"]
                or peso_max_antigo != premio["peso_max"]
                or peso_atual_antigo != novo_peso_atual
            )

            if houve_alteracao_pesos:
                cursor.execute("""
                    INSERT INTO historico_pesos (id_premio, peso_anterior, peso_novo, motivo)
                    VALUES (?, ?, ?, ?)
                """, (
                    existente["id"],
                    peso_atual_antigo,
                    novo_peso_atual,
                    f"Atualização a partir do ficheiro '{origem}'"
                ))

    for linha_bd in premios_bd:
        chave_bd = linha_bd["nome"].strip().lower()
        if chave_bd not in nomes_ficheiro:
            cursor.execute("""
                UPDATE premios
                SET ativo = 0
                WHERE id = ?
            """, (linha_bd["id"],))

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


def registar_jogada(id_participante, email, id_premio, nome_premio, peso_usado):
    conn = ligar_bd()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO jogadas (id_participante, email_snapshot, id_premio, premio_nome, peso_usado)
        VALUES (?, ?, ?, ?, ?)
    """, (id_participante, email, id_premio, nome_premio, peso_usado))

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

    if linha is None:
        conn.close()
        return

    peso_anterior = linha["peso_atual"]

    cursor.execute("""
        UPDATE premios
        SET peso_atual = ?
        WHERE id = ?
    """, (peso_novo, id_premio))

    cursor.execute("""
        INSERT INTO historico_pesos (id_premio, peso_anterior, peso_novo, motivo)
        VALUES (?, ?, ?, ?)
    """, (id_premio, peso_anterior, peso_novo, motivo))

    conn.commit()
    conn.close()


def recalcular_pesos():
    premios = obter_premios_ativos()
    total_jogadas = contar_total_jogadas()

    if not premios:
        return

    soma_pesos_base = sum(float(p["peso_base"]) for p in premios)

    if soma_pesos_base <= 0:
        return

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

        saidas_esperadas = total_jogadas * (peso_base / soma_pesos_base)
        diferenca = saidas_reais - saidas_esperadas

        if saidas_esperadas < 1:
            saidas_esperadas = 1

        desvio_relativo = diferenca / saidas_esperadas
        fator = 1 - (0.25 * desvio_relativo)

        if fator < 0.70:
            fator = 0.70
        elif fator > 1.30:
            fator = 1.30

        peso_novo = peso_base * fator

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
# FUNÇÕES RELACIONADAS COM O EMAIL
# =========================================================
def obter_ou_criar_participante(email):
    conn = ligar_bd()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM participantes WHERE email = ?", (email,))
    participante = cursor.fetchone()

    if participante is None:
        cursor.execute("""
            INSERT INTO participantes (email, tentativas_disponiveis, total_jogadas)
            VALUES (?, 1, 0)
        """, (email,))
        conn.commit()

        cursor.execute("SELECT * FROM participantes WHERE email = ?", (email,))
        participante = cursor.fetchone()

    conn.close()
    return participante


def obter_participante_por_email(email):
    conn = ligar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM participantes WHERE email = ?", (email,))
    participante = cursor.fetchone()
    conn.close()
    return participante


def alterar_tentativas(email, delta):
    conn = ligar_bd()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE participantes
        SET tentativas_disponiveis = tentativas_disponiveis + ?
        WHERE email = ?
    """, (delta, email))
    conn.commit()
    conn.close()


def incrementar_total_jogadas(email):
    conn = ligar_bd()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE participantes
        SET total_jogadas = total_jogadas + 1
        WHERE email = ?
    """, (email,))
    conn.commit()
    conn.close()


def validar_email(email):
    if email is None:
        return False
    email = email.strip()
    return re.match(EMAIL_REGEX, email) is not None


def pedir_email_valido(root):
    while True:
        email = simpledialog.askstring(
            "Identificação",
            "Introduza o seu email para jogar:",
            parent=root
        )

        if email is None:
            return None

        email = email.strip().lower()

        if not validar_email(email):
            messagebox.showerror(
                "Email inválido",
                "Por favor, introduza um email válido.",
                parent=root
            )
            continue

        return email


# =========================================================
# CLASSE PRINCIPAL DA ROLETA
# =========================================================
class RolPremios:
    # Classe principal para gerir a roleta de prémios com interface gráfica
    def __init__(self, root):
        # Inicializa a janela principal e configurações da roleta
        self.root = root
        self.root.title("Roleta da Sorte")
        self.root.geometry("520x720")
        self.root.resizable(False, False)
        self.root.config(bg="#1a1a1a")

        # Configurações visuais da roleta
        self.raio_roleta = 180      # Raio da roleta em píxeis
        self.centro_x = 260         # Coordenada x do centro
        self.centro_y = 260         # Coordenada y do centro

        self.angulo_atual = 0       # Ângulo atual de rotação
        self.a_girar = False        # Indica se está em animação
        self.premios = []           # Lista de prémios disponíveis

        self.email_atual = None
        self.participante_atual = None

        # Canvas para desenhar a roleta estilo casino
        self.canvas = tk.Canvas(root, width=520, height=520, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(pady=8)

        # Etiqueta com email do utilizador atual
        self.label_email = tk.Label(
            root,
            text="Email atual: -",
            font=("Arial", 10, "bold"),
            bg="#1a1a1a",
            fg="#ffffff"
        )
        self.label_email.pack(pady=3)

        # Etiqueta com número de tentativas disponíveis
        self.label_tentativas = tk.Label(
            root,
            text="Tentativas disponíveis: -",
            font=("Arial", 10),
            bg="#1a1a1a",
            fg="#cccccc"
        )
        self.label_tentativas.pack(pady=2)

        # Etiqueta para exibir o prémio sorteado
        self.label_resultado = tk.Label(
            root,
            text="",
            font=("Arial", 13, "bold"),
            bg="#1a1a1a",
            fg="#00ff00"
        )
        self.label_resultado.pack(pady=5)

        # Etiqueta informativa com mensagens ao utilizador
        self.label_info = tk.Label(
            root,
            text="Pronto para jogar.",
            font=("Arial", 9),
            bg="#1a1a1a",
            fg="#aaaaaa",
            justify="center"
        )
        self.label_info.pack(pady=2)

        # Botão principal para girar a roleta
        self.btn_girar = tk.Button(
            root,
            text="Girar!",
            font=("Arial", 12, "bold"),
            command=self.iniciar_girar,
            bg="#ff6600",
            fg="white",
            activebackground="#ff5500",
            activeforeground="white",
            relief="raised",
            padx=20,
            pady=7,
            bd=3
        )
        self.btn_girar.pack(pady=6)

        # Botão para recarregar prémios do ficheiro CSV
        self.btn_recarregar_premios = tk.Button(
            root,
            text="Recarregar prémios",
            font=("Arial", 9),
            command=self.recarregar_premios_do_ficheiro,
            bg="#444444",
            fg="white",
            activebackground="#555555",
            activeforeground="white",
            relief="raised",
            padx=12,
            pady=4,
            bd=2
        )
        self.btn_recarregar_premios.pack(pady=3)

        # Desenha a seta indicadora no topo (triângulo)
        self.canvas.create_polygon(
            260, 50,
            275, 30,
            245, 30,
            fill="#ff6600",
            outline="#ffaa00",
            width=2,
            tags="seta"
        )

        # Carrega os prémios e desenha a roleta inicial
        self.recarregar_premios()
        self.desenhar_roda()
        self.preparar_proximo_participante()

    def atualizar_labels_participante(self):
        # Atualiza os rótulos com informações do utilizador atual
        if self.participante_atual is None:
            self.label_email.config(text="Email atual: -")
            self.label_tentativas.config(text="Tentativas disponíveis: -")
            return

        self.label_email.config(text=f"Email atual: {self.participante_atual['email']}")
        self.label_tentativas.config(
            text=f"Tentativas disponíveis: {self.participante_atual['tentativas_disponiveis']}"
        )

    def preparar_proximo_participante(self):
        # Solicita um novo email e prepara o participante para jogar
        while True:
            email = pedir_email_valido(self.root)

            if email is None:
                self.email_atual = None
                self.participante_atual = None
                self.atualizar_labels_participante()
                self.label_info.config(text="Nenhum email foi introduzido.")
                return

            participante = obter_ou_criar_participante(email)

            if participante["tentativas_disponiveis"] <= 0:
                messagebox.showwarning(
                    "Sem tentativas",
                    "Este email já utilizou todas as tentativas disponíveis.\n"
                    "Introduza outro email.",
                    parent=self.root
                )
                continue

            self.email_atual = email
            self.participante_atual = participante
            self.label_resultado.config(text="")
            self.label_info.config(text="")
            self.atualizar_labels_participante()
            break

    def perguntar_novo_email(self):
        # Avisa o utilizador que terminou as tentativas e pede novo email
        messagebox.showinfo(
            "Fim do jogo",
            "As tentativas deste email terminaram.\n"
            "Será pedido um novo email para a próxima jogada.",
            parent=self.root
        )
        self.preparar_proximo_participante()

    def recarregar_premios_do_ficheiro(self):
        # Recarrega os prémios a partir do ficheiro CSV e atualiza a roleta
        try:
            sincronizar_premios_com_ficheiro()
            self.recarregar_premios()
            self.desenhar_roda()
            self.label_info.config(text="Prémios recarregados com sucesso.")
        except Exception as e:
            messagebox.showerror(
                "Erro ao recarregar prémios",
                f"Não foi possível ler os prémios:\n{e}",
                parent=self.root
            )

    def recarregar_premios(self):
        # Sincroniza os prémios com o ficheiro e calcula o ângulo de cada segmento
        sincronizar_premios_com_ficheiro()
        self.premios = obter_premios_ativos()
        self.numero_segmentos = len(self.premios)
        self.angulo_segmento = 360 / self.numero_segmentos if self.numero_segmentos > 0 else 360

    def desenhar_roda(self):
        # Limpa todos os segmentos anteriores
        self.canvas.delete("segmento")

        # Se não houver prémios, exibe mensagem
        if not self.premios:
            self.canvas.create_text(
                260, 260,
                text="Sem prémios.\nCrie o ficheiro premios.csv\ncom os prémios para exibir.",
                font=("Arial", 12, "bold"),
                justify="center",
                tags="segmento",
                fill="#ffffff"
            )
            return

        # Desenha o fundo externo decorativo (aro)
        self.canvas.create_oval(
            self.centro_x - self.raio_roleta - 8,
            self.centro_y - self.raio_roleta - 8,
            self.centro_x + self.raio_roleta + 8,
            self.centro_y + self.raio_roleta + 8,
            fill="#333333",
            outline="#ffaa00",
            width=4,
            tags="segmento"
        )

        # Desenha cada segmento da roleta estilo casino
        for i, premio in enumerate(self.premios):
            # Calcula o ângulo de início do segmento
            angulo_inicio = self.angulo_atual + (i * self.angulo_segmento)

            # Alterna entre cores casino (vermelho e preto com detalhes dourados)
            if i % 2 == 0:
                cor_fundo = "#cc0000"    # Vermelho casino
            else:
                cor_fundo = "#1a1a1a"    # Preto casino

            # Desenha o arco (segmento) da roleta
            self.canvas.create_arc(
                self.centro_x - self.raio_roleta,
                self.centro_y - self.raio_roleta,
                self.centro_x + self.raio_roleta,
                self.centro_y + self.raio_roleta,
                start=angulo_inicio,
                extent=self.angulo_segmento,
                fill=cor_fundo,
                outline="#ffaa00",  # Borda dourada
                width=2,
                tags="segmento"
            )

            # Se a cor do prémio for especificada, usa-a
            if premio["cor"].strip().lower() != "#000000" and premio["cor"].strip():
                try:
                    self.canvas.create_arc(
                        self.centro_x - self.raio_roleta,
                        self.centro_y - self.raio_roleta,
                        self.centro_x + self.raio_roleta,
                        self.centro_y + self.raio_roleta,
                        start=angulo_inicio,
                        extent=self.angulo_segmento,
                        fill=premio["cor"],
                        outline="#ffaa00",
                        width=2,
                        tags="segmento"
                    )
                except:
                    pass

            # Calcula a posição do texto no meio do segmento
            angulo_meio = angulo_inicio + self.angulo_segmento / 2
            rad = math.radians(angulo_meio)
            x = self.centro_x + 115 * math.cos(rad)
            y = self.centro_y - 115 * math.sin(rad)

            # Desenha o texto do prémio com cor branca para contraste
            self.canvas.create_text(
                x,
                y,
                text=premio["nome"],
                font=("Arial", 9, "bold"),
                width=85,
                justify="center",
                tags="segmento",
                fill="#ffffff"
            )

        # Desenha o círculo central (hub) estilo casino
        raio_hub = 40
        self.canvas.create_oval(
            self.centro_x - raio_hub,
            self.centro_y - raio_hub,
            self.centro_x + raio_hub,
            self.centro_y + raio_hub,
            fill="#ffaa00",              # Dourado
            outline="#333333",
            width=3,
            tags="segmento"
        )

        # Círculo interior do hub
        self.canvas.create_oval(
            self.centro_x - raio_hub + 8,
            self.centro_y - raio_hub + 8,
            self.centro_x + raio_hub - 8,
            self.centro_y + raio_hub - 8,
            fill="#ff8800",              # Laranja
            outline="#ffaa00",
            width=1,
            tags="segmento"
        )

        # Ponto central
        self.canvas.create_oval(
            self.centro_x - 5,
            self.centro_y - 5,
            self.centro_x + 5,
            self.centro_y + 5,
            fill="#333333",
            outline="#ffaa00",
            width=1,
            tags="segmento"
        )

    def escolher_premio_por_peso(self):
        # Seleciona um prémio aleatoriamente baseado nos pesos atuais
        pesos = [float(p["peso_atual"]) for p in self.premios]
        return random.choices(self.premios, weights=pesos, k=1)[0]

    def iniciar_girar(self):
        # Inicia o processo de girar a roleta
        if self.a_girar:
            return

        try:
            self.recarregar_premios()
            self.desenhar_roda()
        except Exception as e:
            messagebox.showerror(
                "Erro nos prémios",
                f"Antes de girar, corrija o ficheiro de prémios:\n{e}",
                parent=self.root
            )
            return

        if not self.premios:
            messagebox.showwarning(
                "Sem prémios",
                "Não existem prémios ativos no ficheiro.",
                parent=self.root
            )
            return

        if self.participante_atual is None:
            self.preparar_proximo_participante()
            if self.participante_atual is None:
                return

        self.participante_atual = obter_participante_por_email(self.email_atual)

        if self.participante_atual["tentativas_disponiveis"] <= 0:
            messagebox.showinfo(
                "Sem tentativas",
                "Este email já não tem tentativas disponíveis.",
                parent=self.root
            )
            self.preparar_proximo_participante()
            return

        alterar_tentativas(self.email_atual, -1)
        incrementar_total_jogadas(self.email_atual)

        self.participante_atual = obter_participante_por_email(self.email_atual)
        self.atualizar_labels_participante()

        self.recarregar_premios()
        premio_escolhido = self.escolher_premio_por_peso()

        self.premio_sorteado = premio_escolhido
        self.indice_premio_sorteado = next(
            i for i, p in enumerate(self.premios) if p["id"] == premio_escolhido["id"]
        )

        self.angulo_inicial_animacao = self.angulo_atual
        voltas_extra = random.randint(4, 6)

        angulo_desejado = 90 - (
            self.indice_premio_sorteado * self.angulo_segmento + self.angulo_segmento / 2
        )

        self.angulo_final_animacao = angulo_desejado + 360 * voltas_extra

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
        # Anima a rotação da roleta com suavização
        if self.frame_atual < self.total_frames:
            # Calcula o progresso com easing ease-out (suavização gradual)
            t = self.frame_atual / self.total_frames
            progresso = 1 - pow(1 - t, 3)

            # Atualiza o ângulo atual interpolado
            self.angulo_atual = (
                self.angulo_inicial_animacao
                + (self.angulo_final_animacao - self.angulo_inicial_animacao) * progresso
            )

            self.desenhar_roda()
            self.frame_atual += 1
            self.root.after(20, self.animar_roda)
        else:
            # Finaliza a animação
            self.angulo_atual = self.angulo_final_animacao % 360
            self.desenhar_roda()
            self.finalizar_giro()

    def finalizar_giro(self):
        # Finaliza o giro e regista o resultado
        premio = self.premio_sorteado

        # Regista a jogada na base de dados
        registar_jogada(
            id_participante=self.participante_atual["id"],
            email=self.participante_atual["email"],
            id_premio=premio["id"],
            nome_premio=premio["nome"],
            peso_usado=float(premio["peso_atual"])
        )

        mensagem_extra = "Tentativa concluída."

        # Verifica se o prémio é "Tente novamente"
        if premio["nome"].strip().lower() == "tente novamente":
            alterar_tentativas(self.email_atual, 1)
            mensagem_extra = "Saiu 'Tente novamente': ganhou mais uma tentativa."

        # Recalcula os pesos baseado no novo histórico
        recalcular_pesos()

        self.participante_atual = obter_participante_por_email(self.email_atual)
        self.recarregar_premios()
        self.atualizar_labels_participante()

        # Exibe o resultado
        self.label_resultado.config(text=f"Prémio: {premio['nome']}")
        self.label_info.config(
            text=(
                f"Email registado: {self.email_atual}\n"
                f"{mensagem_extra}"
            )
        )

        self.a_girar = False
        self.btn_girar.config(state="normal")

        # Se não houver mais tentativas, pede novo email
        if self.participante_atual["tentativas_disponiveis"] <= 0:
            self.root.after(500, self.perguntar_novo_email)


# =========================================================
# ARRANQUE DO PROGRAMA
# =========================================================
if __name__ == "__main__":
    # Cria as tabelas da base de dados
    criar_tabelas()

    # Sincroniza os prémios a partir do ficheiro CSV
    try:
        sincronizar_premios_com_ficheiro()
    except Exception as e:
        print(f"Aviso ao arrancar: {e}")

    # Inicializa a janela principal
    root = tk.Tk()
    app = RolPremios(root)
    root.mainloop()
