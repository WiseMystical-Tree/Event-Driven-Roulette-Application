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
NOME_BD = "Projeto_Roleta_teste.db"
EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"

# O programa procura por premios.csv. Se não existir, não haverá prémios.
FICHEIRO_PREMIOS_CSV = "premios.csv"
# =========================================================
def gerar_cor_aleatoria():
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


def parse_linha_txt(linha):
    """
    Aceita formatos como:
      nome=5€ FNAC
      peso_base=6
      peso_min=3
      peso_max=8
      cor=#FFAA00

    Também aceita:
      nome: 5€ FNAC
    """
    if "=" in linha:
        chave, valor = linha.split("=", 1)
    elif ":" in linha:
        chave, valor = linha.split(":", 1)
    else:
        return None, None

    return chave.strip().lower(), valor.strip()


# =========================================================
# LEITURA DE PRÉMIOS A PARTIR DE CSV
# =========================================================
def ler_premios_csv(caminho):
    premios = []

    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)

        colunas_necessarias = {"nome", "peso_base", "peso_min", "peso_max"}
        colunas_lidas = {c.strip().lower() for c in (leitor.fieldnames or [])}

        if not colunas_necessarias.issubset(colunas_lidas):
            raise ValueError(
                "O ficheiro CSV tem de ter pelo menos as colunas: "
                "nome, peso_base, peso_min, peso_max"
            )

        for i, linha in enumerate(leitor, start=2):
            nome = normalizar_nome_premio(linha.get("nome", ""))

            if not nome:
                raise ValueError(f"Linha {i} do CSV sem nome de prémio.")

            peso_base = texto_para_float(linha.get("peso_base", ""), "peso_base", nome)
            peso_min = texto_para_float(linha.get("peso_min", ""), "peso_min", nome)
            peso_max = texto_para_float(linha.get("peso_max", ""), "peso_max", nome)

            cor = str(linha.get("cor", "") or "").strip()
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


def ler_premios_txt(caminho):
    """
    Formato do TXT:
    Cada prémio é um bloco separado por linha em branco.

    Exemplo:
    nome=5€ FNAC
    peso_base=6
    peso_min=3
    peso_max=8

    nome=Tente novamente
    peso_base=15
    peso_min=10
    peso_max=18
    cor=#FF33A1
    """
    with open(caminho, "r", encoding="utf-8-sig") as f:
        conteudo = f.read()

    blocos = [b.strip() for b in conteudo.split("\n\n") if b.strip()]
    premios = []

    for idx, bloco in enumerate(blocos, start=1):
        dados = {}

        for linha in bloco.splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue

            chave, valor = parse_linha_txt(linha)
            if chave is None:
                raise ValueError(
                    f"Bloco {idx}: linha inválida '{linha}'. "
                    f"Use 'campo=valor' ou 'campo: valor'."
                )

            dados[chave] = valor

        nome = normalizar_nome_premio(dados.get("nome", ""))
        if not nome:
            raise ValueError(f"Bloco {idx}: falta o campo 'nome'.")

        if "peso_base" not in dados or "peso_min" not in dados or "peso_max" not in dados:
            raise ValueError(
                f"Bloco do prémio '{nome}': faltam campos obrigatórios "
                f"(peso_base, peso_min, peso_max)."
            )

        peso_base = texto_para_float(dados["peso_base"], "peso_base", nome)
        peso_min = texto_para_float(dados["peso_min"], "peso_min", nome)
        peso_max = texto_para_float(dados["peso_max"], "peso_max", nome)

        if peso_min > peso_base or peso_base > peso_max:
            raise ValueError(
                f"No prémio '{nome}' os pesos têm de respeitar: "
                f"peso_min <= peso_base <= peso_max."
            )

        cor = dados.get("cor", "").strip() or gerar_cor_aleatoria()

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

            # Se o peso base mudou muito e o peso atual ainda era igual ao base antigo,
            # acompanha o novo base.
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

        self.email_atual = None
        self.participante_atual = None

        self.canvas = tk.Canvas(root, width=500, height=450, bg="white")
        self.canvas.pack(pady=10)

        self.label_email = tk.Label(root, text="Email atual: -", font=("Arial", 11, "bold"))
        self.label_email.pack()

        self.label_tentativas = tk.Label(root, text="Tentativas disponíveis: -", font=("Arial", 11))
        self.label_tentativas.pack()

        self.label_resultado = tk.Label(root, text="", font=("Arial", 16, "bold"))
        self.label_resultado.pack(pady=10)

        self.label_info = tk.Label(
            root,
            text="Pronto para jogar.",
            font=("Arial", 10),
            justify="center"
        )
        self.label_info.pack(pady=5)

        self.btn_girar = tk.Button(
            root,
            text="Girar!",
            font=("Arial", 12, "bold"),
            command=self.iniciar_girar
        )
        self.btn_girar.pack(pady=15)

        self.btn_recarregar_premios = tk.Button(
            root,
            text="Recarregar prémios do ficheiro",
            font=("Arial", 10),
            command=self.recarregar_premios_do_ficheiro
        )
        self.btn_recarregar_premios.pack(pady=5)

        self.canvas.create_polygon(240, 15, 260, 15, 250, 30, fill="black", tags="seta")

        self.recarregar_premios()
        self.desenhar_roda()
        self.preparar_proximo_participante()

    def atualizar_labels_participante(self):
        if self.participante_atual is None:
            self.label_email.config(text="Email atual: -")
            self.label_tentativas.config(text="Tentativas disponíveis: -")
            return

        self.label_email.config(text=f"Email atual: {self.participante_atual['email']}")
        self.label_tentativas.config(
            text=f"Tentativas disponíveis: {self.participante_atual['tentativas_disponiveis']}"
        )

    def preparar_proximo_participante(self):
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
        messagebox.showinfo(
            "Fim do jogo",
            "As tentativas deste email terminaram.\n"
            "Será pedido um novo email para a próxima jogada.",
            parent=self.root
        )
        self.preparar_proximo_participante()

    def recarregar_premios_do_ficheiro(self):
        try:
            sincronizar_premios_com_ficheiro()
            self.recarregar_premios()
            self.desenhar_roda()
            self.label_info.config(text="Prémios recarregados a partir do ficheiro com sucesso.")
        except Exception as e:
            messagebox.showerror(
                "Erro ao recarregar prémios",
                f"Não foi possível ler os prémios:\n{e}",
                parent=self.root
            )

    def recarregar_premios(self):
        sincronizar_premios_com_ficheiro()
        self.premios = obter_premios_ativos()
        self.numero_segmentos = len(self.premios)
        self.angulo_segmento = 360 / self.numero_segmentos if self.numero_segmentos > 0 else 360

    def desenhar_roda(self):
        self.canvas.delete("segmento")

        if not self.premios:
            self.canvas.create_text(
                250, 220,
                text="Sem prémios.\nCrie o ficheiro com o nome premios.csv com os prémios para mostrar.",
                font=("Arial", 14, "bold"),
                justify="center",
                tags="segmento"
            )
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

            self.canvas.create_text(
                x,
                y,
                text=premio["nome"],
                font=("Arial", 9, "bold"),
                width=85,
                justify="center",
                tags="segmento"
            )

    def escolher_premio_por_peso(self):
        pesos = [float(p["peso_atual"]) for p in self.premios]
        return random.choices(self.premios, weights=pesos, k=1)[0]

    def iniciar_girar(self):
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
        if self.frame_atual < self.total_frames:
            t = self.frame_atual / self.total_frames
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

        registar_jogada(
            id_participante=self.participante_atual["id"],
            email=self.participante_atual["email"],
            id_premio=premio["id"],
            nome_premio=premio["nome"],
            peso_usado=float(premio["peso_atual"])
        )

        mensagem_extra = "Tentativa concluída."

        if premio["nome"].strip().lower() == "tente novamente":
            alterar_tentativas(self.email_atual, 1)
            mensagem_extra = "Saiu 'Tente novamente': ganhou mais uma tentativa."

        recalcular_pesos()

        self.participante_atual = obter_participante_por_email(self.email_atual)
        self.recarregar_premios()
        self.atualizar_labels_participante()

        self.label_resultado.config(text=f"Prémio: {premio['nome']}")
        self.label_info.config(
            text=(
                f"Email registado: {self.email_atual}\n"
                f"{mensagem_extra}"
            )
        )

        self.a_girar = False
        self.btn_girar.config(state="normal")

        if self.participante_atual["tentativas_disponiveis"] <= 0:
            self.root.after(500, self.perguntar_novo_email)


# =========================================================
# ARRANQUE DO PROGRAMA
# =========================================================
if __name__ == "__main__":
    criar_tabelas()

    try:
        sincronizar_premios_com_ficheiro()
    except Exception as e:
        print(f"Aviso ao arrancar: {e}")

    root = tk.Tk()
    app = RolPremios(root)
    root.mainloop()
