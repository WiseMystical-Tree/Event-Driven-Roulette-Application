import sqlite3
import tkinter as tk
import random
import math

conn = sqlite3.connect('Projeto_Roleta.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS premios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        probabilidade REAL NOT NULL,
        stock_atual INTEGER,
        stock_inicial INTEGER,
        peso_base INTEGER NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS probabilidades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_premio INTEGER NOT NULL,
        prob_atual REAL NOT NULL,
        registado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_premio) REFERENCES premios(id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        idade INTEGER,
        UNIQUE(nome, idade)
    )
''')

cursor.execute("INSERT OR IGNORE INTO usuarios (nome, idade) VALUES (?, ?)", ('Ana', 28))
cursor.execute("INSERT OR IGNORE INTO usuarios (nome, idade) VALUES (?, ?)", ('Bruno', 34))

conn.commit()
conn.close()
print("Base de dados criada e dados inseridos com sucesso.")

class RodaPremios:
    def __init__(self, root):
        self.root = root
        self.root.title("Roleta de Prémios")
        
        # Configurações da roda
        self.premios = ["100€", "50€", "Jackpot", "Tente Novamente", "20€", "10€", "500€", "Sem Prémio"]
        self.cores = ["#FF5733", "#33FF57", "#3357FF", "#FF33A1", "#A133FF", "#33FFF5", "#F5FF33", "#FF8C33"]
        self.angulos = 360 / len(self.premios)
        self.angulo_atual = 0
        self.velocidade = 0
        
        # Canvas para desenhar a roda
        self.canvas = tk.Canvas(root, width=400, height=400)
        self.canvas.pack()
        
        # Desenhar a roda inicialmente
        self.desenhar_roda()
        
        # Indicador (seta)
        self.canvas.create_polygon(190, 10, 210, 10, 200, 30, fill="black")
        
        # Botão
        self.btn_girar = tk.Button(root, text="Girar!", command=self.iniciar_girar)
        self.btn_girar.pack(pady=20)
        
        # Label resultado
        self.label_resultado = tk.Label(root, text="", font=("Arial", 16))
        self.label_resultado.pack()

    def desenhar_roda(self):
        self.canvas.delete("segmento")
        for i, premio in enumerate(self.premios):
            angulo_inicio = self.angulo_atual + (i * self.angulos)
            self.canvas.create_arc(10, 10, 390, 390, 
                                   start=angulo_inicio, 
                                   extent=self.angulos, 
                                   fill=self.cores[i], 
                                   tags="segmento")
            
            # Adicionar texto do prémio
            rad = math.radians(angulo_inicio + self.angulos/2)
            x = 200 + 120 * math.cos(rad)
            y = 200 - 120 * math.sin(rad)
            self.canvas.create_text(x, y, text=premio, font=("Arial", 10, "bold"), tags="segmento")

    def iniciar_girar(self):
        self.velocidade = random.uniform(15, 25) # Velocidade inicial aleatória
        self.animar_roda()

    def animar_roda(self):
        if self.velocidade > 0.1:
            self.angulo_atual += self.velocidade
            self.velocidade *= 0.98 # Desaceleração
            self.desenhar_roda()
            self.root.after(20, self.animar_roda) # Atualiza a cada 20ms
        else:
            self.finalizar_giro()

    def finalizar_giro(self):
        # Calcular qual prémio parou no topo (90 graus)
        indice = int(((360 - (self.angulo_atual % 360) + 90) % 360) / self.angulos)
        premio_final = self.premios[indice]
        self.label_resultado.config(text=f"Prémio: {premio_final}")

if __name__ == "__main__":
    root = tk.Tk()
    app = RodaPremios(root)
    root.mainloop()