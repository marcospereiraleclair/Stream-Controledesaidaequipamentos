# 💻 Sistema de Liberação de Saída de Equipamentos

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red?logo=streamlit)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-yellow?logo=pandas)
![Matplotlib](https://img.shields.io/badge/Matplotlib-Charts-lightblue?logo=plotly)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📘 Summary
Aplicação em **Streamlit** para controle de saída e entrada de equipamentos corporativos com autenticação por perfil, leitura de QR Code e dashboard de acompanhamento.

---

## 🧾 Description
O sistema permite que **colaboradores**, **supervisores**, **portaria** e **administradores** controlem a movimentação de equipamentos de forma simples e centralizada.  
As ações são registradas em arquivos `.csv` e apresentadas em tempo real em dashboards interativos.

### 🔹 Funcionalidades principais
- Login com diferentes perfis (colaborador, portaria, supervisor, admin).  
- Registro de saídas com **formulário manual** ou via **QR Code**.  
- Autorização de saída por supervisores.  
- Confirmação e registro de entrada pela portaria.  
- Dashboard com métricas e gráficos.  
- Logs automáticos de movimentações.

---

## ⚙️ Tecnologias Utilizadas
- **Python 3.11+**
- **Streamlit**
- **Pandas**
- **Matplotlib**
- **Unicodedata / Regex**
- **CSV / Base64 / OS**

---

## 📁 Estrutura de Diretórios
projeto/
├── templates/
│ └── 234x234.png # Logo da empresa
├── ativos_glpi.csv # Base de ativos exportada do GLPI
├── saida_equipamentos.csv # Registros de saídas
├── saida_dashboard.csv # Dados para o dashboard
├── main.py # Código principal (Streamlit)
├── requirements.txt # Dependências do projeto
└── README.md
