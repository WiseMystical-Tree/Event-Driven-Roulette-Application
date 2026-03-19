# 🎰 Projeto Roleta — Prize Roulette

A casino-style prize roulette application built with Python, designed to run on a touchscreen computer. Players spin a wheel to win prizes, with full inventory tracking, player registration, and spin history logging.

---

## 📋 Table of Contents

- [About the Project](#-about-the-project)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Database Schema](#-database-schema)
- [Getting Started](#-getting-started)
- [Usage](#-usage)
- [Roadmap](#-roadmap)

---

## 📖 About the Project

This project was developed as a university assignment. It consists of a touchscreen-friendly roulette wheel interface where users can register, spin the wheel, and win prizes drawn from a limited inventory. All activity is stored in a local SQLite database.

---

## ✨ Features

- 🎡 Animated casino-style spinning wheel
- 👤 Player registration with name and age
- 🎁 Prize inventory with limited stock
- ⚖️ Weighted prize probabilities (rarer prizes are harder to win)
- 📊 Spin history and statistics tracking
- 📱 Touchscreen-optimised UI

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3 |
| UI | Tkinter |
| Database | SQLite3 (built-in) |

No external dependencies required — everything runs on the Python standard library.

---

## 📁 Project Structure

```
Projeto_Roleta/
├── main.py               # App entry point, Tkinter UI
├── database.py           # All database logic (init, queries, inserts)
├── wheel.py              # Spinning wheel animation (Canvas)
├── config.py             # Prize list, colours, settings
└── Projeto_Roleta.db     # SQLite database (auto-created on first run)
```

---

## 🗄️ Database Schema

The app uses a local SQLite database with the following tables:

### `premios` — Prize catalogue
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| nome | TEXT | Prize name |
| probabilidade | REAL | Base probability |
| stock_atual | INTEGER | Current remaining stock |
| stock_inicial | INTEGER | Original stock amount |
| peso_base | INTEGER | Relative spin weight |

### `probabilidades` — Probability history
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| id_premio | INTEGER | Foreign key → premios |
| prob_atual | REAL | Recorded probability |
| registado_em | TIMESTAMP | When it was recorded |

### `usuarios` — Players
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| nome | TEXT | Player name |
| idade | INTEGER | Player age |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- No additional packages needed

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/Projeto_Roleta.git
cd Projeto_Roleta
```

2. Run the app:
```bash
python main.py
```

The database file `Projeto_Roleta.db` will be created automatically on first run.

---

## 🖥️ Usage

1. Launch the app on a touchscreen computer
2. Enter your name to register as a player
3. Tap **Rodar** to spin the wheel
4. The wheel selects a prize based on weighted probabilities
5. If stock is available, the prize is awarded and inventory is updated
6. View spin history and stats from the main menu

---

## 🗺️ Roadmap

- [x] Database setup and schema
- [x] Player registration
- [ ] Spinning wheel animation
- [ ] Prize awarding logic
- [ ] Admin panel to manage prizes and stock
- [ ] Stats and history dashboard
- [ ] Touchscreen UI polish

---

## 👨‍💻 Author

Developed for a university project.

---

## 📄 License

This project is for academic use only.
