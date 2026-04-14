# 🎰 Projeto Roleta — Prize Roulette

A casino-style prize roulette application built with Python, designed to run on a touchscreen computer. Players spin a wheel to win prizes, with full inventory tracking, player registration, and spin history logging.

---

## 📋 Table of Contents

- [About the Project](#about-the-project)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Roadmap](#roadmap)

---

## 📖 About the Project

This project was developed as a university assignment. It consists of a touchscreen-friendly roulette wheel interface where users can register, spin the wheel, and win prizes drawn from a limited inventory. All activity is stored in a local SQLite database.

---

## ✨ Features

- 🎡 Animated casino-style spinning wheel
- 📧 Player registration via email (one spin per email)
- 🎁 Prize inventory with limited stock
- ⚖️ Adaptive weighted probabilities (auto-adjusts after each spin to stay balanced)
- 📊 Full spin history and weight change logging
- 📱 Touchscreen-optimised UI (launches fullscreen)

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
├── Projeto_Roleta.py     # Full application (DB logic, UI, wheel animation)
└── Projeto_Roleta.db     # SQLite database (auto-created on first run)
```

---

## 🗄️ Database Schema

The app uses a local SQLite database with the following tables:

### `premios` — Prize catalogue
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| nome | TEXT | Prize name (unique) |
| cor | TEXT | Wheel segment colour |
| stock_atual | INTEGER | Current remaining stock |
| stock_inicial | INTEGER | Original stock amount |
| peso_base | REAL | Base spin weight |
| peso_atual | REAL | Current adjusted weight |
| peso_min | REAL | Minimum allowed weight |
| peso_max | REAL | Maximum allowed weight |
| ativo | INTEGER | Whether prize is active (1/0) |
| tenta_novamente | INTEGER | Grants an extra spin if won (1/0) |

### `participantes` — Players
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| email | TEXT | Player email (unique) |
| tentativas_disponiveis | INTEGER | Remaining spins |
| total_jogadas | INTEGER | Total spins used |
| criado_em | TIMESTAMP | Registration timestamp |

### `jogadas` — Spin history
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| id_participante | INTEGER | Foreign key → participantes |
| email_snapshot | TEXT | Email at time of spin |
| id_premio | INTEGER | Foreign key → premios |
| premio_nome | TEXT | Prize name at time of spin |
| peso_usado | REAL | Weight used for this spin |
| data_jogada | TIMESTAMP | When the spin occurred |

### `historico_pesos` — Weight change log
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| id_premio | INTEGER | Foreign key → premios |
| peso_anterior | REAL | Weight before change |
| peso_novo | REAL | Weight after change |
| motivo | TEXT | Reason for the change |
| registado_em | TIMESTAMP | When the change was recorded |

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
python Projeto_Roleta.py
```

The database file `Projeto_Roleta.db` will be created automatically on first run.

---

## 🖥️ Usage

1. Launch the app on a touchscreen computer (opens fullscreen automatically)
2. Enter your **email** to register as a player
3. Tap **Girar!** to spin the wheel
4. The wheel selects a prize based on adaptive weighted probabilities
5. If "Tente novamente" is landed on, the player gets a bonus spin
6. Once all attempts are used, a new email is requested for the next player

---

## 🗺️ Roadmap

- [x] Database setup and schema
- [x] Player registration (email-based)
- [x] Spinning wheel animation
- [x] Adaptive prize weight recalculation
- [x] Touchscreen UI (fullscreen)
- [ ] Admin panel to manage prizes and stock
- [ ] Stats and history dashboard

---

## 👨‍💻 Author

Developed for a university project.

---

## 📄 License

This project is for academic use only.
